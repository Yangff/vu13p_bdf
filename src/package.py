import re

data = open("database/xcvu13pfhgb2104pkg.txt", "r").read().splitlines()

data_start = False
DATA_REGEX = r"^(?P<Pin>[\dA-Z]+)\s+(?P<PinName>[\dA-Z_]+)\s+(?P<MBG>[\dA-Z_]+)\s+(?P<Bank>[\dA-Z_]+)\s+(?P<IOT>[\dA-Z_]+)\s+(?P<SLR>[\dA-Z_]+)"

pins = {}
pinnames = {}
pin_order = []

for i in data:
    i = i.strip()
    if i == "Pin   Pin Name                            Memory Byte Group  Bank  I/O Type  Super Logic Region":
        data_start = True
        continue
    if i == "" or not data_start:
        continue
    if i.startswith("Total Number of Pins"):
        break
    # process data
    
    tokens = re.match(DATA_REGEX, i)
    if tokens:
        group = tokens.groupdict()
        pins[group["Pin"]] = {
            "Pin": group["Pin"],
            "PinName": group["PinName"],
            "MBG": group["MBG"],
            "Bank": group["Bank"],
            "IOT": group["IOT"],
            "SLR": group["SLR"],
            "_order": len(pin_order)
        }
        pinnames[group["PinName"]] = pins[group["Pin"]]
        pin_order.append(group["Pin"])

def get_diffpair(pin, pn = 'P'):
    pin_data = pins[pin]
    if pin_data['IOT'] == 'HP':
        order = pin_data['_order']
        if pn == 'P':
            return pin_order[order - 1]
        else:
            return pin_order[order + 1]
    if pin_data['IOT'] == 'GTY':
        # MGTREFCLK, MGTYTX, MGTYRX
        if pin_data['PinName'].startswith('MGTYRX') or pin_data['PinName'].startswith('MGTREFCLK') or pin_data['PinName'].startswith('MGTYTX'):
            # MGTYTXN\d_\d+ -> MGTYTXP\d_\d+
            newname = ""
            if pn == 'P':
                newname = pin_data['PinName'].replace('P', 'N')
            else:
                newname = pin_data['PinName'].replace('N', 'P')
            return pinnames[newname]['Pin']

def get_txrxpair(pin):
    pin_data = pins[pin]
    if pin_data['IOT'] == 'GTY':
        if pin_data['PinName'].startswith('MGTYRX'):
            return pinnames[pin_data['PinName'].replace('MGTYRX', 'MGTYTX')]['Pin']
        if pin_data['PinName'].startswith('MGTYTX'):
            return pinnames[pin_data['PinName'].replace('MGTYTX', 'MGTYRX')]['Pin']
    return pin

def gen_rx_databasse(database):
    newdb = {}
    for k, pins in database.items():
        newk = k.replace("tx", "rx")
        newdb[newk] = {i: get_txrxpair(v) for i, v in pins.items()}
    return newdb