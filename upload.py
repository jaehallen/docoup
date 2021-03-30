import os
import requests
import re
from zlib import crc32

WT_API = 'https://wetransfer.com/api/v4/transfers'
API_LINKS = WT_API + '/link'
API_FILES = WT_API + '/{link_id}/files'
API_PART_PUT = API_FILES + '/{file_id}/part-put-url'
API_FINALIZE_MPP = API_FILES + '/{file_id}/finalize-mpp'
API_FINALIZE = WT_API + '/{link_id}/finalize'

fs = lambda f : {"name": os.path.basename(f), "size": os.path.getsize(f)}

def _session():
    s = requests.Session()
    r = s.get('https://wetransfer.com/')
    token = re.search('name="csrf-token" content="([^"]+)"', r.text)
    s.headers.update({'x-csrf-token': token.group(1), 'x-requested-with': 'XMLHttpRequest'})

    return s

def _links(filename, session):
    data = {
        "files": [fs(filename)],
        "message": '',
        "ui_language": "en",
    }

    r = session.post(API_LINKS, json=data)
    # print(r.json())
    return r.json()

def _files(filename, session, link_id):
    r = session.post(API_FILES.format(link_id=link_id), json=fs(filename))
    # print(r.json())
    return r.json()

def _chunks(filename, chunk_size):
    with open(filename, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)

            if not len(chunk):
                break

            yield chunk

def _part_put(filename, session, link_id, file_id, chunk_size):
    for chunk_number, chunk in enumerate(_chunks(filename, chunk_size), start=1):
        data = {
            "chunk_number" : chunk_number,
            "chunk_size": len(chunk),
            "chunk_crc": crc32(chunk) & 0xffffffff,
        }

        # print(data)
        r = session.post(
            API_PART_PUT.format(link_id=link_id, file_id=file_id),
            json=data
        )

        url = r.json()['url']
        # print(url)
        requests.options(
            url,
            headers={
                "Access-Control-Request-Method": "PUT",
                "Origin": "https://wetransfer.com"
            }
        )

        requests.put(url, data=chunk)

    r = session.put(
        API_FINALIZE_MPP.format(link_id=link_id, file_id=file_id),
        json={"chunk_count": chunk_number}
    )

    return r.json()

def _finalize(link_id, session):
    r = session.put(API_FINALIZE.format(link_id=link_id))
    return r.json()

def upload_file(filename):
    session = _session()
    link_id = _links(filename, session)['id']
    response = _files(filename, session, link_id)
    file_id = response['id']
    chunk_size = response['chunk_size']
    _part_put(filename, session, link_id, file_id, chunk_size)

    return _finalize(link_id, session)['shortened_url'].rstrip()
def log_data(filename, wt, nte_link=''):
    logPath = './upload_log'
    if not os.path.exists(logPath):
        os.mkdir(logPath)

    with open(os.path.join(logPath,'log.txt'), "a+") as f:
        f.seek(0)
        data = f.read(100)
        if len(data) > 0:
            f.write("\n")
        f.write(f"{filename.rstrip()} | {wt.rstrip()} | {nte_link.rstrip()}")

def post_logs(ssID, uploadedFile, wtLink, nteLink=''):
    ssLink = f'https://script.google.com/a/notetakerstaff.com/macros/s/{ssID}/exec'
    data = {
        'uploadedFile' : uploadedFile,
        'wtLink': wtLink,
        'nteLink': nteLink,
    }
    try:
        r = requests.post(ssLink, json=data)
    except:
        log_data(uploadedFile, wtLink, nteLink)
        print('Failed to log uploaded file')
