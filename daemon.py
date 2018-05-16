import base64
import io
import os
from configparser import ConfigParser
from sys import stderr

import barcode
import click
import flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlsoup import SQLSoup
from twisted.internet import reactor
from twisted.python import log
from twisted.python.threadpool import ThreadPool
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from weasyprint import HTML


PKG_PADDING = 9
PKG_PREFIX = 'DR'
PKG_POSTFIX = 'M'
SUBMITTER_ID = '54'

PKG_S2D = 1234566
PKG_D2S = 1234567

SOURCE = [
    'Národní technická knihovna',
    'Technická 2710/6',
    '160 80 Praha 6-Dejvice',
    'Česká Republika',
    '+420 232 002 535',
]

DEST = [
    'Moravská zemská knihovna',
    'Kounicova 65a',
    '601 87 Brno-střed',
    'Česká Republika',
    '+420 541 646 201',
]


def calculate_pkg_checksum(number):
    FACTORS = [1, 8, 6, 4, 2, 3, 5, 9, 7]
    checksum = 0
    for factor in FACTORS[::-1]:
        number, module = divmod(number, 10)
        checksum += factor * module
    a = checksum % 11
    if a > 1:
        return 11 - a
    if a == 1:
        return 0
    if a == 0:
        return 5

def create_pkg_id(prefix, postfix, submitter_id, pkg_number):
    tmp_pkg_number = '{:0{}d}'.format(pkg_number, PKG_PADDING - len(submitter_id))
    checksum = calculate_pkg_checksum(int('{}{}'.format(submitter_id, tmp_pkg_number)))
    return '{}{}{}{}{}'.format(
        prefix, submitter_id, tmp_pkg_number, checksum, postfix
    )

def gen_b64_barcode(code, text=''):
    byte_stream = io.BytesIO()
    barcode.generate('code128', code, output=byte_stream, text=text)
    return base64.b64encode(byte_stream.getvalue())

def generate_pdf(src_to_dst, dst_to_src):
    data = {}

    data['barcode1_text'] = src_to_dst['package_id']
    data['barcode1_barcode'] = gen_b64_barcode(data['barcode1_text']).decode("utf-8")
    data['sender1'] = src_to_dst['sender']
    data['addressee1'] = src_to_dst['addressee']

    data['barcode2_text'] = dst_to_src['package_id']
    data['barcode2_barcode'] = gen_b64_barcode(data['barcode2_text']).decode("utf-8")
    data['sender2'] = dst_to_src['sender']
    data['addressee2'] = dst_to_src['addressee']

    # html = HTML(string=HTML_TEMPLATE.format(**data))
    tmp_html = flask.render_template('ziskej-cp_stitek.html', **data)
    # print(tmp_html)
    html = HTML(string=tmp_html)

    result = html.write_pdf()
    return result


def make_site(db, debug=False):
    app = flask.Flask('.'.join(__name__.split('.')[:-1]))
    app.secret_key = os.urandom(16)
    app.debug = debug

    @app.route('/')
    def postal_label():
        src_to_dst = {
            'package_id': create_pkg_id(PKG_PREFIX, PKG_POSTFIX, SUBMITTER_ID, PKG_S2D),
            'sender': SOURCE,
            'addressee': DEST,
        }
        dst_to_src = {
            'package_id': create_pkg_id(PKG_PREFIX, PKG_POSTFIX, SUBMITTER_ID, PKG_D2S),
            'sender': DEST,
            'addressee': SOURCE,
        }
        pdf = generate_pdf(src_to_dst, dst_to_src)
        response = flask.make_response(pdf)
        response.headers.set('Content-Disposition', 'attachment', filename='stitek.pdf')
        response.headers.set('Content-Type', 'application/pdf')
        return response

    return app

@click.command()
@click.option(
    '--config',
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False,
        writable=False, readable=True, resolve_path=True
    ),
    help='path to config file',
)
def main(config):
    cfg = ConfigParser()
    cfg.read(config)

    # Start Twisted logging to console.
    log.startLogging(stderr)

    # Read database configuration options.
    db_url = cfg.get('database', 'url')

    # Read website configuration options.
    http_debug = cfg.getboolean('http', 'debug', fallback=False)
    http_host = cfg.get('http', 'host', fallback='localhost')
    http_port = cfg.getint('http', 'port', fallback=5000)
    http_pool = cfg.getint('http', 'pool_size', fallback=4)

    # Default to much saner database query defaults and always
    # commit and/or flush statements explicitly.
    # factory = sessionmaker(autocommit=False, autoflush=False)

    # Prepare database connection with table reflection.
    engine = create_engine(db_url)
    session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
    db = SQLSoup(engine, session=session)

    # Extract manager options, sans the pool_size we handle here.
    # pool_size = int(manager_opts.pop('pool_size', 2))
    pool_size = 2

    # Set the correct thread pool size for the manager.
    reactor.suggestThreadPoolSize(pool_size)

    # Prepare the website that will get exposed to the users.
    site = make_site(db, debug=http_debug)

    # Prepare WSGI site with a separate thread pool.
    pool = ThreadPool(http_pool, http_pool, 'http')
    site = Site(WSGIResource(reactor, pool, site))
    pool.start()

    # Bind the website to it's address.
    reactor.listenTCP(http_port, site, interface=http_host)

    # Run the Twisted reactor until the user terminates us.
    reactor.run()

    # Kill the HTTP ThreadPool.
    pool.stop()

if __name__ == '__main__':
    main()


# vim:set sw=4 ts=4 et:
# -*- coding: utf-8 -*-
