# Luigi task to write clean files to aws
import luigi
import json
from luigi.s3 import S3Target, S3Client
from datetime import date, timedelta
from functions_pl import *
import pandas as pd

# External task at the bottom of our dependancy graph,
# only looks to see if output of cronjob exists,
# by default from yesterday.
class local_raw_json(luigi.ExternalTask):
    date = luigi.DateParameter(default = date.today()-timedelta(1)) 

    def output(self):
        return luigi.LocalTarget('spotify/json/spotify_tracks_%s.json' % 
                                 self.date.strftime('%Y-%m-%d'))
    
# Task that runs our deduplicate() on local file 
# and writes the output to S3 bucket.
class spotify_clean_aws(luigi.Task):
    date = luigi.DateParameter(default = date.today()-timedelta(1)) 
    
    def requires(self):
        return self.clone(local_raw_json)
        
    def run(self):   
        with self.input().open('r') as in_file:
            data = deduplicate(in_file)
            
        with self.output().open('w') as out_file:
            json.dump(data, out_file)

    def output(self):
        client = S3Client(host = 's3.us-east-2.amazonaws.com')
        return S3Target('s3://myspotifydata/spotify_tracks_%s.json' % 
                        self.date.strftime('%Y-%m-%d'), 
                        client=client)

            
# Task that merges the 7 daily datasets, 
# parses relevant fields, deduplicates records
# and stores the result in S3.
class spotify_merge_weekly_aws(luigi.Task):
    date = luigi.DateParameter(default = (date.today()-timedelta(8)))
    daterange = luigi.IntParameter(7)

    def requires(self):
        # take data from the 7 days following date param (8 days prior to current date by default)
        return [spotify_clean_aws(i) for i in [self.date + timedelta(x) for x in range(self.daterange)]]
     
    def run(self):
        results = []
        for file in self.input():
            
            with file.open('r') as in_file:
                data = json.load(in_file)
                parsed = parse_json(data)
                
            results.extend(parsed)
        # merging of daily data creates dupe records still
        result = {v['played_at']:v for v in results}.values()
        
        with self.output().open('w') as out_file:
            json.dump(result, out_file)
            
    def output(self):
        client = S3Client(host = 's3.us-east-2.amazonaws.com')
        return S3Target('s3://myspotifydata/spotify_week_%s.json' % 
                        (self.date.strftime('%Y-%m-%d') + '_' + str(self.daterange)), 
                         client=client)
    
            
# Task to aggregate weekly data and create playlist
class spotify_morning_playlist(luigi.Task):
    date = luigi.DateParameter(default = (date.today()-timedelta(8)))
    daterange = luigi.IntParameter(7)

    def requires(self):
        return self.clone(spotify_merge_weekly_aws)
    
    def run(self):
        
        with self.input().open('r') as in_file:
            res_code = create_playlist(in_file, self.date)      
        # write to file if succesful
        if (res_code == 201):
            with self.output().open('w') as out_file:
                json.dump(res_code, out_file)
    
    def output(self):
        client = S3Client(host = 's3.us-east-2.amazonaws.com')
        return S3Target('s3://myspotifydata/spotify_top10_%s.json' % 
                        (self.date.strftime('%Y-%m-%d') + '_' + str(self.daterange)), 
                        client=client)


if __name__ == '__main__':
    luigi.run()
        
           
