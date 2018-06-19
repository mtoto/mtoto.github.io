library(dplyr)
library(kableExtra)
library(async)
library(rvest)
library(xml2)

# read data from alexa topsites output files
read_alexa_txt <- function(filenames) {
        list_of_dat <- lapply(filenames, 
                              function(x) read.table(x,
                                                     skip = 6,
                                                     header = FALSE,
                                                     stringsAsFactors = FALSE)[,1])
        
        Reduce(union, list_of_dat)
        
}

# async function to scrape privacy statement given an url.
http_content <- function(url) {
        def <- http_get(url)$
                then(function(response) {
                        if(response$status_code == 200) {
                                rawToChar(response$content) %>%
                                        read_xml(as_html = TRUE)  %>%
                                        html_nodes("p") %>%
                                        html_text()
                        } 
                }
                )$
                catch(error = function(...) setNames("error", url))
}

# function to filter only policies that have 
# gdpr in the body and returns vector.
filter_gdpr_policies <- function(list_of_policies) {
        # drop list members wtih shorter than 10 elements
        element_length <- lengths(list_of_policies)
        usable_policies_final <- list_of_policies[element_length>10]
        # concatenate into one string
        usable_policies_final<-lapply(usable_policies_final,paste0,collapse=" ")
        # only keep policies that explicitly refer to gdpr
        is_gdpr <- Reduce(union, list(grep("General Data Protection Regulation", usable_policies_final),
                                      grep("GDPR", usable_policies_final),
                                      grep("gdpr", usable_policies_final)))
        usable_gdpr_pols <- unlist(usable_policies_final[is_gdpr])
        
        return(usable_gdpr_pols)
        
}

# function to parse privacy statement from 
# usable policies dataset.
read_policy <- function(file) {
        policy <- readLines(file)
        policy <- policy[-grep("SECTION|POLICY", policy)]
        policy <- gsub("<SUBTITLE>|</SUBTITLE>|<SUBTITLE />|<SUBTEXT>|</SUBTEXT>","",policy)
        policy <- paste0(policy, collapse = " ")
        
        return(policy)
}

# get lines containing the url from usable policy dataset.
get_policy_line <- function(file) {
        policy <- readLines(file)
        policy <- policy[grep("POLICY", policy)]
        
        return(policy)
}

# get policy urls from usable policy dataset
get_policy_url <- function(list_of_files) {
        usable_urls <- lapply(list_of_files, 
                              function(x) get_policy_line(
                                      paste("./corpus/", x,sep="")))
        usable_urls <- unlist(usable_urls)
        usable_urls <- strsplit(usable_urls, "\"")
        usable_urls <- unlist(usable_urls)
        usable_urls <- usable_urls[grep("http", usable_urls)]
        
        return(usable_urls)
}

# strip urls of prefixes and suffixes for
# comparison with alexa topsites list of urls.
strip_url <- function(urls) {
        split_urls <- strsplit(urls,"/")
        split_urls <- sapply(split_urls, "[[", 3)
        split_urls <- gsub("www." , "", split_urls)
        
        return(split_urls)
        
}

# function to convert table to kable styled
# confusion matrix.
confusion_kable <- function(conf_table, caption = "") {
        conf_table %>% mutate(
                preds = row.names(.),
                nee = ifelse(row.names(.) == "nee",
                             cell_spec(nee, background = "green", color = "white"),
                             cell_spec(nee, background = "red", color = "white")),
                ja = ifelse(row.names(.) == "ja",
                            cell_spec(ja, background = "green", color = "white"),
                            cell_spec(ja, background = "red", color = "white"))) %>%
                 select(c(3,1,2)) %>% 
                kableExtra::kable(escape = F,caption = caption) %>%
                column_spec(3, width = "1.5cm") %>%
                kable_styling("hover", full_width = F) %>%
                add_header_above(c("", "obs", " "))
       
}

# function to get accuracy n sensitivity
get_metrics <- function(preds, y) {
        c(sum(diag(table(preds,y))) / sum(table(preds,y)),
          sum(table(preds,y)[1,1]) / sum(table(preds,y)[,1]))
}



