py-html-mailer
==============

These are scripts that I use to send e-mail marketing messages through a private Exchange server. I needed to send professional-style HTML e-mail newsletters to campus distribution lists, which are inaccessible from typical e-mail marketing platforms (e.g. MailChimp, ConstantContact, etc.). So I wrote my own scripts to do this.

The script `archiveVersion.py` takes an HTML e-mail and assembles versions both for sending and for archival viewing through the Web. The images from the message are copied to a Web-accessible directory on the user's account, and the image sources for the sending and archival versions are automatically updated to point to that Wed-accessible directory. Once this is done and an HTML message (with optional plain text version) is assembled, `mailscript4.py` takes care of sending the message through the Exchange server (or any other SMTP-capable server).

The input file and other options are configured with a user-constructed INI file (example to come).
