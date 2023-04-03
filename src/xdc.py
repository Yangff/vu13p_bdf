import re

def parse_xdc(xdc_content):
    parsed_data = []

    # Split the content by lines
    lines = xdc_content.split("\n")

    properties = {}
    ports = {}
    iostd = {}

    for line in lines:
        line = line.split("#")[0]
        line = line.strip()
        
        # Ignore empty lines and comments
        if not line or line.startswith("#"):
            continue

        # Split the line by spaces, ignoring spaces inside curly braces
        tokens = re.match(r"\b(set_property)\s+(?P<PROPERTY>[\w.]+)\s+(?P<OBJECT>\S+)\s+\[(?P<VALUE>.*)\]", line)

        if tokens:
            group = tokens.groupdict()
            prop = group["PROPERTY"].upper().strip()
            obj = group["OBJECT"].upper().strip()
            val = group["VALUE"].lower().strip()
            
            # if the propertty is empty, init with {}
            if prop not in properties:
                properties[prop] = {}

            properties[prop][obj] = val
            if prop == 'PACKAGE_PIN':
                port_assign = re.match(r"\b(get_ports)\s+\{*(?P<port>[^\}]+)\}*", val)
                if port_assign:
                    port = port_assign.groupdict()["port"].strip()
                    port_ary = re.match(r"(?P<portname>.*)\[(?P<id>\d+)\]", port)
                    idx = 0
                    if port_ary:
                        port = port_ary.groupdict()["portname"].strip()
                        idx = int(port_ary.groupdict()["id"].strip())
                    if port not in ports:
                        ports[port] = {}
                    ports[port][idx] = obj
            if prop == 'IOSTANDARD':
                port_assign = re.match(r"\b(get_ports)\s+\{*(?P<port>[^\}]+)\}*", val)
                if port_assign:
                    port = port_assign.groupdict()["port"].strip()
                    port_ary = re.match(r"(?P<portname>.*)\[(?P<id>\d+)\]", port)
                    if port_ary:
                        port = port_ary.groupdict()["portname"].strip()
                    iostd[port] = obj

            
    return {"properties": properties, "ports": ports, "iostd": iostd}