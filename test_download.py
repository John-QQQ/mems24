import requests

dl = "https://www.dropbox.com/scl/fi/qxv6bsvew6y8fonvse3k3/01227500814_2.jpg?rlkey=4ofjnxun5pwyrghsyo4iikdqo&dl=0,https://www.dropbox.com/scl/fi/iqb8yeiln0z5pnx3flku1/01227500814_1.jpg?rlkey=izjmd6bjxmxt1l0nw7hxw3c7k&dl=0"

def replace_link(original_link: str):
    original_link = original_link.strip()
    # Replace dl=0 with raw=1

    original_link = original_link.replace("dl=0", "raw=1")
    return original_link
    

def test_download(link):
    response = requests.get(link)
    print(response)
    with open("test.jpg", "wb") as f:
        f.write(response.content)

if __name__ == "__main__":
    print(replace_link(dl))
    print("Testing download")
    test_download(replace_link(dl))