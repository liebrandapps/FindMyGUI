import datetime
import imaplib
import urllib.parse
from email.message import Message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import time


class IMAPUpdater:
    TAG = "[IMAP]"
    SUBJECT = "AirTag Location Update"

    def __init__(self, context):
        self.ctx = context
        self.mail = None
        self._terminate = False


    def login(self):
        cfg = self.ctx.cfg
        if cfg.imap_useSSL:
            self.mail = imaplib.IMAP4_SSL(host=cfg.imap_host)
        else:
            self.mail = imaplib.IMAP4(host=cfg.imap_host)
        self.mail.login(cfg.imap_user, cfg.imap_password)
        if cfg.imap_folder is not None and len(cfg.imap_folder) > 0 and cfg.imap_folder != '/':
            # check for folder, if reports are to be stored in a folder instead of INBOX
            # create the folder, in case it does not exist.
            found = False
            status, lst = self.mail.list()
            for f in lst:
                tmp = f.decode('UTF-8')
                tmp1 = tmp.split('"."')
                folder = tmp1[1].strip()
                if folder == cfg.imap_folder:
                    found = True
                    break
            if not found:
                self.mail.create(cfg.imap_folder)

    def logout(self):
        self.mail.logout()

    def storeMessagePlain(self):
        msg = Message()
        msg['From'] = self.ctx.cfg.imap_sender
        msg['Subject'] = IMAPUpdater.SUBJECT
        msg.set_payload("Test")
        self.mail.append(self.ctx.cfg.imap_folder, '', imaplib.Time2Internaldate(time()), str(msg).encode('utf-8'))

    def storeMessageHtml(self):
        gMapUrl = "https://www.google.com/maps/dir/"
        bingUrl = "https://bing.com/maps/default.aspx?sp="
        ctrlong = 0
        ctrlat = 0
        cnt = 0
        pts = ""
        imgUrl = "https://github.com/liebrandapps/FindMyGUI/blob/master/www/"
        CRLF = '<p>'
        tagListHtml = ""
        for tag in self.ctx.airtags.values():
            name = tag.name
            longitude = tag.longitude
            latitude = tag.latitude
            lastSeen = datetime.datetime.fromtimestamp(tag.lastSeen)
            gl = 'https://maps.google.com/maps?q=' + str(latitude) + ',' + str(longitude)
            tagListHtml += name + CRLF
            tagListHtml += lastSeen.strftime('%Y-%m-%d %H:%M:%S') + CRLF
            tagListHtml += gl + CRLF
            tagListHtml += CRLF
            imgId = tag.imgId
            gMapUrl += "/" + str(latitude) + "," + str(longitude)
            if len(pts) > 0:
                pts += "~"
            pts += "point." + str(latitude) + "_" + str(longitude) + "_" + urllib.parse.quote_plus(name) + \
                   "_" + urllib.parse.quote_plus("Last Update: " + lastSeen.strftime("%H:%M:%S %d.%m.%Y")) + \
                   "_" + urllib.parse.quote_plus("https://github.com/liebrandapps") + \
                   "_" + urllib.parse.quote_plus(imgUrl + imgId + ".png?raw=true")
            ctrlong += longitude
            ctrlat += latitude
            cnt += 1
        bingUrl += pts
        msg = MIMEMultipart('alternative')
        msg['From'] = self.ctx.cfg.imap_sender
        msg['Subject'] = "AirTag Location Update"
        text = "AirTag Location Update\n\n" + bingUrl
        html = """\
        <html>
          <head>
          </head>
          <body>
            <p>Hi!<br>
               List of locations<br>
               <br>"""
        html += tagListHtml
        html += """<hr>
               List of locations (combined)<br>
               Click this link to open in browser <a href=" """
        html += bingUrl
        html += """">link</a>.
            </p>
                
          </body>
        </html>
        """
        part1 = MIMEText(text, 'plain')
        part2 = MIMEText(html, 'html')
        msg.attach(part1)
        msg.attach(part2)
        status, data = self.mail.append(self.ctx.cfg.imap_folder, '\\Seen' if self.ctx.cfg.imap_markAsRead else '', imaplib.Time2Internaldate(time()), str(msg).encode('utf-8'))
        if status == "NO":
            self.ctx.log.error(f"Error creating email in Mailbox: {str(data)}")

    def removeOldReports(self):
        self.mail.select(self.ctx.cfg.imap_folder if not len(self.ctx.cfg.imap_folder) == 0 else 'Inbox')
        typ, data = self.mail.search(None, '(SUBJECT "%s")' % IMAPUpdater.SUBJECT)
        for num in data[0].split():
            self.mail.store(num, '+FLAGS', '\\Deleted')
        self.mail.expunge()
