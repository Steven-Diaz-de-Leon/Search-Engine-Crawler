import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from urllib.parse import urldefrag
from urllib.parse import urljoin
from simhash import Simhash, SimhashIndex
from PartA import tokenize
from PartA import computeWordFrequencies


visitedUrls = []
unique_urls = []
longestPage = ["", 0]
most_common = {}
subdomains = {}
index = SimhashIndex([], k=3)
duplicate_urls = 0
total_urls = 0
noftimes = 0

#converts visible text into single string
def get_features(text):
    text = text.lower()
    text = re.sub(r'[^\w]+', '', text)
    return text

#determines if the site has been seen before based on the similarities of the visible text using simhash
def seen(text, url):
    global duplicate_urls
    global total_urls
    hash = Simhash(get_features(text))
    dups = index.get_near_dups(hash)
    print("total duplicate sites: ", duplicate_urls)
    #print("total unique sites: ", total_urls)
    if len(dups) == 0:
        index.add(url, hash)
        total_urls += 1
        return False
    else:
        duplicate_urls += 1
        print(url)
        print(dups)
        return True

def scraper(url, resp):
    print(resp.raw_response)
    global noftimes
    noftimes += 1
    print("total urls: ", noftimes)
    if(resp.status > 399):
        return []

    #count unique pages visited
    d_url = urldefrag(url)
    if url not in unique_urls:  # Add unique links (not sure if it should be here)
        unique_urls.append(d_url)

    #extract sites visible text
    soup = BeautifulSoup(resp.raw_response.content, "lxml")
    [s.extract() for s in soup(['style', 'script', '[document]', 'head', 'title'])]
    visible_text = soup.getText()
    # print(visible_text)

    #if we've seen a textually similar site dont waste time on it
    if (seen(visible_text, url)):
        return []
    links = extract_next_links(url, resp)

    #find longest page
    wordList = tokenize(visible_text)
    if len(wordList) > longestPage[1]:
        longestPage[0] = url
        longestPage[1] = len(wordList)

    #find most common words
    frequencies = computeWordFrequencies(wordList)
    f = open("stop_words.txt")
    for word in frequencies:
        if word in f.read():
            continue
        if word not in most_common:
            most_common[word] = frequencies[word]
        else:
            most_common[word] += frequencies[word]

    ret = [link for link in links if is_valid(link, resp)]
    return ret


def extract_next_links(url, resp):
    print("NOW WORKING ON: " + url)

    data = resp.raw_response.content
    soup = BeautifulSoup(data, 'html.parser')
    tempRet = []

    tags = soup.find_all('a')
    for tag in tags:
        link = urldefrag(tag.get('href'))[0]
        #print("link from tag: ", link)
        #print("original url: ", url)
        if "http" not in str(link) or "https" not in str(link):
            joined_url = urljoin(url, link)
            #print("joined_url: ", joined_url)
            tempRet.append(joined_url)
        else:
            tempRet.append(link)

    return tempRet

def is_valid(url, resp):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        regexBool = not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv|nb|ppsx|mat|apk|war"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz|Z|txt|odc)$", parsed.path.lower())

        blacklist = ["img_", "/files/pdf", "?replytocom", "?share=", "?action=", "/pix/", "archive.ics.uci.edu/ml/"]
        if any(s in url for s in blacklist):
            return False


        #list of valid domains
        #change this to regex or smth
        valid_netlocs = [".ics.uci.edu", ".cs.uci.edu", ".informatics.uci.edu", ".stat.uci.edu",
                         ".today.uci.edu/department/information_computer_sciences/"]


        current_netloc = parsed.netloc
        valid_domain = False
        for netloc in valid_netlocs:
            if netloc in url:
                valid_domain = True

        current_netloc = current_netloc.replace("www", "")

        #find number of subdomains in ics.uci.edu domain
        if "ics.uci.edu" in current_netloc:
            subdomain = current_netloc.split("ics.uci.edu")
            if subdomain[0] != "":
                if current_netloc not in subdomains:
                    subdomains[current_netloc] = 1
                elif url not in unique_urls:
                    subdomains[current_netloc] += 1

        return regexBool and valid_domain

    except TypeError:
        print("TypeError for ", parsed)
        raise