import base64
import io

import barcode
from weasyprint import HTML
from flask import Flask, make_response

HTML_TEMPLATE = '''
<html>

<head>
    <meta charset="UTF-8">
    <style>
        @page {{
            size: A4;
            margin: 0;
        }}

        html,
        body {{
            width: 210mm;
            height: 297mm;
            margin: 0;
        }}

        * {{
            box-sizing: border-box;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .label {{
            width: 105mm;
            height: 148mm;
            margin: 0cm;
            position: relative;
        }}

        .pos1 {{
            position: absolute;
            top: 0mm;
            left: 0mm;
        }}

        .pos2 {{
            position: absolute;
            top: 0mm;
            left: 105mm;
        }}

        .pos3 {{
            position: absolute;
            top: 148mm;
            left: 0mm
        }}

        .pos4 {{
            position: absolute;
            top: 148mm;
            left: 105mm;
        }}

        .bar-code-row {{
            position: absolute;
            top: 0mm;
            left: 0mm;
            width: 105mm;
            padding-top: 9mm;
        }}

        .sender-row {{
            position: absolute;
            top: 50mm;
            left: 0mm;
            width: 105mm;
        }}

        .addressee-row {{
            position: absolute;
            top: 100mm;
            left: 0mm;
            width: 105mm;
        }}

        .bar-code-img {{
            width: 100%;
            height: 25mm;
        }}

        .delivery {{
            width: 30%;
            float: left;
            text-align: center;
            padding-left: 9mm;
        }}

        .bar-code {{
            width: 70%;
            float: right;
            text-align: right;
            padding-right: 8mm;
            padding-left: 8mm;
        }}

        .bar-code-text {{
            text-align: center;
            font-size: 5mm;
        }}

        .delivery-dr {{
            font-size: 10mm;
        }}

        .delivery-type {{
            width: 20mm;
            font-size: 15mm;
            font-weight: bold;
            background-color: black;
            color: white;
        }}

        .address {{
            padding-left: 9mm;
            padding-right: 9mm;
        }}

        .address-header {{
            font-size: 3mm;
        }}

        .address-address {{
            padding-left: 5mm;
            font-size: 4mm;
        }}

        .address-row {{
            margin: 0;
            margin-top: 1.5mm;
        }}

        .row {{
            padding-top: 9mm;
            display: flex;
        }}
    </style>
</head>

<body>
    <div class="label pos1">
        <div class="bar-code-row">
            <div class="delivery">
                <div class="delivery-dr">
                    DR
                </div>
                <span class="delivery-type">
                    &nbsp;A&nbsp;
                </span>
            </div>
            <div class="bar-code">
                <img class="bar-code-img" src="data:image/svg+xml;base64,{barcode1_barcode}"/>
                <div class="bar-code-text">
                    {barcode1_text}
                </div>
            </div>
        </div>
        <div class="sender-row">
            <div class="address">
                <div class="address-header">
                    Odesílatel/Sender:
                </div>
                <div class="address-address">
                    <p class="address-row">{sender1[0]}</p>
                    <p class="address-row">{sender1[1]}</p>
                    <p class="address-row">{sender1[2]}</p>
                    <p class="address-row">{sender1[3]}</p>
                    <p class="address-row">{sender1[4]}</p>
                </div>
            </div>
        </div>
        <div class="addressee-row">
            <div class="address">
                <div class="address-header">
                    Adresát/Addressee:
                </div>
                <div class="address-address">
                    <p class="address-row">{addressee1[0]}</p>
                    <p class="address-row">{addressee1[1]}</p>
                    <p class="address-row">{addressee1[2]}</p>
                    <p class="address-row">{addressee1[3]}</p>
                    <p class="address-row">{addressee1[4]}</p>
                </div>
            </div>
        </div>
    </div>

    <div class="label pos2">
        <div class="bar-code-row">
            <div class="delivery">
                <div class="delivery-dr">
                    DR
                </div>
                <span class="delivery-type">
                    &nbsp;A&nbsp;
                </span>
            </div>
            <div class="bar-code">
                <img class="bar-code-img" src="data:image/svg+xml;base64,{barcode2_barcode}"/>
                <div class="bar-code-text">
                    {barcode2_text}
                </div>
            </div>
        </div>
        <div class="sender-row">
            <div class="address">
                <div class="address-header">
                    Odesílatel/Sender:
                </div>
                <div class="address-address">
                    <p class="address-row">{sender2[0]}</p>
                    <p class="address-row">{sender2[1]}</p>
                    <p class="address-row">{sender2[2]}</p>
                    <p class="address-row">{sender2[3]}</p>
                    <p class="address-row">{sender2[4]}</p>
                </div>
            </div>
        </div>
        <div class="addressee-row">
            <div class="address">
                <div class="address-header">
                    Adresát/Addressee:
                </div>
                <div class="address-address">
                    <p class="address-row">{addressee2[0]}</p>
                    <p class="address-row">{addressee2[1]}</p>
                    <p class="address-row">{addressee2[2]}</p>
                    <p class="address-row">{addressee2[3]}</p>
                    <p class="address-row">{addressee2[4]}</p>
                </div>
            </div>
        </div>
    </div>
</body>

</html>'''

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
        # print(checksum, factor, factor * module)
    a = checksum % 11
    # print(checksum, a)
    if a > 1:
        return 11 - a
    if a == 1:
        return 0
    if a == 0:
        return 5

def create_pkg_id(prefix, postfix, submitter_id, pkg_number):
    tmp_pkg_number = '{:0{}d}'.format(pkg_number, PKG_PADDING - len(submitter_id))
    checksum = calculate_pkg_checksum(int('{}{}'.format(submitter_id, tmp_pkg_number)))
    # print(tmp_pkg_number)
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

    html = HTML(string=HTML_TEMPLATE.format(**data))
    result = html.write_pdf()
    return result

app = Flask(__name__)

@app.route('/')
def stitek_cp():
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
    response = make_response(pdf)
    response.headers.set('Content-Disposition', 'attachment', filename='stitek.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response
