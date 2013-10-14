# py-html-mailer

These are scripts that I use to send e-mail marketing messages through a private Exchange server. I needed to send professional-style HTML e-mail newsletters to campus distribution lists, which are inaccessible from typical e-mail marketing platforms (e.g. MailChimp, ConstantContact, etc.). So I wrote my own scripts to do this.

The script `archiveVersion.py` takes an HTML e-mail and assembles versions both for sending and for archival viewing through the Web. The images from the message are copied to a Web-accessible directory on the user's account, and the image sources for the sending and archival versions are automatically updated to point to that Web-accessible directory. Once this is done and an HTML message (with optional plain text version) is assembled, `mailscript4.py` takes care of sending the message through the Exchange server (or any other SMTP-capable server).

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

## Install

Clone the project, make the scripts executable, and link them to a `bin` directory on the user's account. (Here, `~/local/bin`, which is created here.

    $ git clone git://github.com/ntmoe/py-html-mailer.git
    $ cd py-html-mailer
    $ chmod u+x archiveVersion.py
    $ chmod u+x mailscript4.py
    $ cd
    $ mkdir -p ~/local/bin
    $ cd local/bin
    $ ln -s ~/py-html-mailer/archiveVersion.py archiveVersion
    $ ln -s ~/py-html-mailer/mailscript4.py mailscript4

Be sure to add this `bin` directory to your `$PATH`.

## Use

Create an HTML message. Our example here is `jan_newsletter.html`. If you're using images, place them in the same directory as the HTML file and refer to the images using relative links.

The input file and other options are configured with a user-constructed INI file. Here's an example of this file, which is named `config.ini` here, but can be named anything you'd like:

    # Email header information
        # The address format is the same as that which MS Outlook uses if you were to copy
        # addresses from an e-mail in Outlook and paste it into a plain text file.
        # Enclose the addresses in quotes. I've given a few examples of the format here.
    From = "Foo Communications <communications@foo.com>"
    Reply-To = "Doe, John <jdoe@foo.com>"
    To = "Jane Austen <jausten@bar.com>; Dickens, Charles <cdickens@foo.com>"
    Subject = "January newsletter"
    
    # Email server information
    server = exchange.foo.com
    port = 25
    
    # Project structure information
        # The file you're working from.
    original_HTML = jan_newsletter.html
    www-docs_root = ~/www-docs
        # The URL to your user directory.
    web_path_root = http://users.foo.com/~johndoe/
        # The path inside www-docs where you'd like your images and archive version to live.
    path_to_site_folder = newsletter/2012/jan/
    
    # Options (answer True or False)
        # If you'd like to move the files to the Web-accessible directory
    publish_files = True
        # If you'd like to use the Premailer service to tidy up your message before it's sent
    use_premailer = True
        # If you'd like to use lynx to generate the plain text version (instead of Premailer)
    use_lynx_for_text = False
        # If you'd like to allow mailscript4.py to send your message. This is a safety measure.
    send_message = True
    
Once you have this, you can process the HTML file, make sending and archive versions and send it off:
    
    $ archiveVersion config.ini
    $ mailscript4 config.ini
    
You will be prompted for your e-mail account's password after the last command.

##What each script does

### `archiveVersion.py`

1. Generates a tracking pixel (a 1x1 transparent GIF), saves it with the same name as the working HTML file (here, `jan_newsletter.gif`), and attaches it to the end of the message
2. Replaces the title of the HTML document with the subject line listed in the INI file. If there is no `<title>...<\title>` in the document already, one is created
2. Goes through each image and adds dimensions to the `<img />` tags
3. Finds images and other files linked by relative links and stages them for publishing to the Web-accessible directory
4. Uses HTML Tidy and `BeautifulSoup` to create versions for mailing and for archiving
5. If enabled in the INI file, sends the HTML to the Premailer service to remove comments from the HTML and to change the URLs from relative links to absolute links that point to files on the Web-accessible directory. Premailer also sends back a text-only version of the HTML. The script removes the CDATA tags that Premailer inserts sometimes.
6. If `use_lynx_for_text` is set to False in the INI file, Premailer's plain text version is used to generate a `txt` file. Otherwise, it is generated with `lynx`.
7. The files referred to by relative links are published to the Web-accessible directory. The script takes care of creating the paths and setting Web permissions.
7. Multiple files are generated:
    - `jan_newsletter-archive.html`: The version published to the Web-accessible directory
    - `jan_newsletter-mail.html`: The HTML version that will be mailed
    - `jan_newsletter.txt`: The plain text version that will be mailed
    - `jan_newsletter.gif`: The tracking pixel

At this point, you can create a link to the tracking pixel in the Web-accessible directory on a service like `bit.ly` and insert the tracking link's URL into `jan_newsletter-mail.html`.

### `mailscript4.py`

1. Uses the INI file to find the `-mail.html` and `.txt` versions
2. Uses the INI file to create Subject, From, To, Reply-To fields
3. Joins the `-mail.html` and `.txt` versions into a message
4. Using the account listed in the To field, sends the message using the server settings in the INI file and asks for the account's password to do so.

### Tags for the archive versions

I use MailChimp-style tags when constructing my e-mail messages. When `archiveVersion.py` detects `*|ARCHIVE|*` in the HTML source, it replaces that tag with the URL for the archive version that will be posted online. This will usually be in a section like this:

    <!-- *|IFNOT:ARCHIVE_PAGE|* -->
    <td valign="top" width="190">
      <div>
        Is this email not displaying correctly?<br/><a href="*|ARCHIVE|*" target="_blank">View it in your browser</a>.
      </div>
    </td>
    <!-- *|END:IF|* -->

`archiveVersion.py` will look for HTML bracketed by `<!-- *|IFNOT:ARCHIVE_PAGE|* -->` and `<!-- *|END:IF|* -->` and remove it from the archive version of the message.
