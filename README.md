py-html-mailer
==============

These are scripts that I use to send e-mail marketing messages through a private Exchange server. I needed to send professional-style HTML e-mail newsletters to campus distribution lists, which are inaccessible from typical e-mail marketing platforms (e.g. MailChimp, ConstantContact, etc.). So I wrote my own scripts to do this.

The script `archiveVersion.py` takes an HTML e-mail and assembles versions both for sending and for archival viewing through the Web. The images from the message are copied to a Web-accessible directory on the user's account, and the image sources for the sending and archival versions are automatically updated to point to that Web-accessible directory. Once this is done and an HTML message (with optional plain text version) is assembled, `mailscript4.py` takes care of sending the message through the Exchange server (or any other SMTP-capable server).

The input file and other options are configured with a user-constructed INI file. Here's an example of this file:

    # Email header information
    From = "Foo Communications <communications@foo.com>"
    Reply-To = "Doe, John <jdoe@foo.com>"
    To = "Jane Austen <jausten@bar.com>; Dickens, Charles <cdickens@foo.com>"
    Subject = "January newsletter"
    
    # Email server information
    server = exchange.foo.com
    port = 25
    
    # Project structure information
    original_HTML = jan_newsletter.html
    www-docs_root = ~/www-docs
    web_path_root = http://users.foo.com/~johndoe/
    path_to_site_folder = newsletter/2012/jan/
    
    # Options
    publish_files = True
    use_premailer = True
    use_lynx_for_text = False
    send_message = True


Requires the following Python packages which are normally not part of a standard installation:
  - `BeautifulSoup`
  - `configobj`
  - `PIL`

Also requires HTML Tidy, which can be obtained  and installed to a user's home directory (here, `~/local`) with

    $ wget ftp://mirror.internode.on.net/pub/gentoo/distfiles/tidy-20090325.tar.bz2
    $ tar xvjf tidy-20090325.tar.bz2
    $ cd tidy-20090325
    $ sh build/gnuauto/setup.sh
    $ ./configure --prefix=$HOME/local
    $ make install
