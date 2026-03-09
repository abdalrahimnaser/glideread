import requests
import json

# Replace these with your actual IDs
NOTION_TOKEN = "="
DATABASE_ID = "="

headers = {
    "Authorization": "Bearer " + NOTION_TOKEN,
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28", # Use the latest API version
}

def add_row_to_notion(text_content, status_label):
    url = "https://api.notion.com/v1/pages"
    
    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": { 
                "title": [ #
                    {
                        "text": {
                            "content": text_content
                        }
                    }
                ]
            },
            "Status": { # col name
                "status": {  # col property
                    "name": status_label # ?
                }
            }
        }
    }

    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        print("Success! Row added.")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

# Example usage
# add_row_to_notion("Automated Task from Python", "Done")