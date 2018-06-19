source("functions.R")

# 0.1 retrieve url's from usable privacy dataset
usable_urls <- get_policy_url(list.files("./corpus/"))
split_urls <- strip_url(usable_urls)

# 0.2 create all combo's of suffix / alexa urls
dat <- read_alexa_txt(paste("./alexa/", 
                            list.files("./alexa/"),
                            sep = ""))

to_drop <- intersect(split_urls, dat)
to_drop_usable <- which(split_urls %in% dat)

suffix <- c("/privacy_policy","/privacy-policy","/privacy")
urls <- paste("https://www.", dat[!dat %in% to_drop], sep = "")

all_urls<-as.vector(outer(urls, suffix, paste, sep=""))

# 1. scrape alexa topsites urls
policies_list<-synchronise(async_map(
        all_urls, http_content)
)
gdpr_pols <- filter_gdpr_policies(policies_list)

# 2. scape usable gdpr dataset (if updated?)
usable_policies_list<-synchronise(async_map(
        usable_urls, http_content)
)
usable_gdpr_pols <- filter_gdpr_policies(usable_policies_list)

# 3. read usable old dataset 
usable_policies_old <- lapply(list.files("./corpus/"), 
                              function(x) read_policy(
                                      paste("./corpus/", x,sep="")))
usable_policies_old<-lapply(usable_policies_old,paste0,collapse=" ")
usable_policies_old <- unlist(usable_policies_old)
usable_policies_old <- trimws(usable_policies_old)

# 4. get data ready
old_df <- data.frame(policy = usable_policies_old, is_gdpr = "nee")
gdpr_df <- data.frame(policy = c(gdpr_pols, usable_gdpr_pols), is_gdpr = "ja")

data <- rbind(old_df, gdpr_df)

data$policy <- gsub("[^[:alnum:] ]", "", data$policy)
data$policy <- gsub("\\d", "", data$policy)
data<-data[!duplicated(data),]

saveRDS(data,"data.rds")