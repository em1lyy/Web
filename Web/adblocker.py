import os.path

from PyQt5 import QtWebEngineCore

authority_blacklist = []

# If a hosts file is supplied, we can use it as a simple ad blocking filter list.
if os.path.isfile("hosts"):
    with open("hosts") as fobject:
        lines = fobject.read().splitlines()
        for line in lines:
            # Ignore comments.
            if line.startswith("#"):
                continue
            url = line.split()
            if len(url) > 0:
                url = url[-1]
                authority_blacklist.append(url)
        del lines
        # print (authority_blacklist) # This is pretty unnecessary

class AdBlocker(QtWebEngineCore.QWebEngineUrlRequestInterceptor):
    """This is an ad-blocking request interceptor that can be assigned to QtWebEngine."""
    
    active = True
    
    def set_active(self, active):
        self.active = active
    
    def interceptRequest(self, info):
        # Add "Do Not Track"-Header
        info.setHttpHeader(b'DNT', b'1')
        # If adblocking is active, block requests
        if self.active: 
            if info.requestUrl().host() in authority_blacklist:
                info.block(True)
                print("Blocked ad from: " + info.requestUrl().host())
            
