import nltk
import requests
from html import unescape
from bs4 import BeautifulSoup
import string



# Download NLTK stopwords and punkt tokenizer (if not already downloaded)
nltk.download('stopwords')
nltk.download('punkt')

from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

# Set your user agent string
user_agent = "Your_User_Agent_String"



def fetch_pages(query):
  query = query.strip().lower()
  query = query.translate(str.maketrans('', '', string.punctuation))


  # Wikipedia API search for the most relevant page
  url = f"https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={query}"

  headers = {
      'User-Agent': user_agent
  }

  response = requests.get(url, headers=headers)

  if response.status_code == 200:
      data = response.json()
      if data.get('query') and data['query'].get('search'):
          search_results = data['query']['search']
          if search_results:
              results = {}
              for result in search_results[:min(len(search_results), 3)]:
                page_title = result['title']
                
                # Fetch the entire page content using action=parse
                page_url = f"https://en.wikipedia.org/wiki/{page_title.replace(' ', '_')}"
                parse_url = f"https://en.wikipedia.org/w/api.php?action=parse&page={page_title}&format=json"
                
                parse_response = requests.get(parse_url, headers=headers)
                if parse_response.status_code == 200:
                    parse_data = parse_response.json()
                    if parse_data.get('parse') and parse_data['parse'].get('text'):
                        page_content = parse_data['parse']['text']['*']
                        
                        # Parse HTML content using BeautifulSoup to remove unwanted elements
                        soup = BeautifulSoup(page_content, 'html.parser')
                        
                        # Remove citations, references, tables, and other unwanted elements
                        for tag in soup(['sup', 'table', 'span', 'style']):
                            tag.decompose()
                        
                        # Get the text content
                        clean_text = unescape(soup.get_text())
                        
                        #print(f"Found relevant page: {page_title}")
                        #print(f"Page URL: {page_url}")
                        results[page_url] = [page_title, clean_text]
                        #print(f"Clean text content:\n{clean_text}")
                    else:
                        print("No 'parse' or 'text' key found in the parse response.")
                else:
                  print("Failed to fetch parse data from Wikipedia API.")
          else:
              print("No search results found.")
      else:
          print("No 'query' or 'search' key found in the response.")
  else:
      print("Failed to fetch data from Wikipedia API.")

  return query, results    



from sentence_transformers import SentenceTransformer, util
import nltk
import torch

model = SentenceTransformer('paraphrase-MiniLM-L6-v2')


def get_result(query, pages):

  embeddings = []

  for key in pages.keys():
    # Sample Wikipedia paragraphs (list of paragraphs)
    wikipedia_paragraphs = pages[key][1].split('\n\n') # Your list of Wikipedia paragraphs
    for paragraph in wikipedia_paragraphs:
      embeddings.append([paragraph, model.encode(paragraph, convert_to_tensor=True), key])


  # Generate SBERT embedding for the query
  query_embedding = model.encode(query, convert_to_tensor=True)

  # Calculate cosine similarity between query embedding and all other embeddings
  similarities = []
  for emb_tuple in embeddings:
      emb = emb_tuple[1]
      sim = util.pytorch_cos_sim(query_embedding, emb.unsqueeze(0))
      similarities.append(sim)

  # Find the index of the most similar paragraph
  most_similar_index = max(enumerate(similarities), key=lambda x: x[1])[0]
  print(most_similar_index)
  # Retrieve the most similar paragraph and its associated text
  return embeddings[most_similar_index]


from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Sample chatbot logic
def chatbot_response(query):
    # Implement your chatbot logic here
    # For this example, let's echo the user's message
    query, pages = fetch_pages(query)
    #print(query)
    info = get_result(query, pages)
    return str(info[2]) + "\n" + str(info[0])

@app.route("/")
def index():
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.get_json()
    user_query = data['user_input']
    user_id = data.get('user_id', 'unknown')
    #print(user_query)
    response = chatbot_response(user_query)
    return jsonify({'response': response})

if __name__ == '__main__':
    app.run(debug=True)  
  
