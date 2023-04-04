import os
from pathlib import Path
import sys
from typing import List
from xdc import parse_xdc # type: ignore

COMPANY_NAME = "A company"
# override company name with environment variable
if "COMPANY_NAME" in os.environ:
    COMPANY_NAME = os.environ["COMPANY_NAME"]

URL = "http://"
# override url with environment variable
if "URL" in os.environ:
    URL = os.environ["URL"]

FILE_VERSION = "1.0"
# override file version with environment variable
if "FILE_VERSION" in os.environ:
    FILE_VERSION = os.environ["FILE_VERSION"]

# change cwd to project root
project_root = Path(__file__).parent.parent
print(project_root)
os.chdir(str(project_root))

sys.path.insert(0, str(project_root))

from generated.board import *
from generated.preset import *
from generated.part0_pins import *
from generated import board as B

from package import get_diffpair, gen_rx_databasse

xdcs = {}

# iterator over xdc files in xdc directory
for xdc_file in Path("xdc").glob("*.xdc"):
    # extract filename without extension and path
    xdcname = xdc_file.stem
    # open and read xdc file
    print("Parsing xdc file: " + xdcname)
    with open(xdc_file, "rb") as f:
        xdc_file = f.read().decode('utf-8')
        # parse xdc file
        xdcs[xdcname] = parse_xdc(xdc_file)
        #print(xdcs[xdcname])

# define pins data
# part0_pins

part_info = PartInfo(part_name="xcvu13p-fhgb2104-2-i")
pins = Pins()
part_info.pins = [pins]
added_pins = {}
gIndex = 0
def add_pin(name, loc, iostd = None):
    global gIndex, added_pins
    if name in added_pins:
        if loc != added_pins[name]:
            raise Exception("Pin " + name + " already added with different location: " + added_pins[name] + " != " + loc)
        return
    added_pins[name] = loc
    pin = Pin(index = str(gIndex), name = name, loc = loc, iostandard=iostd)
    gIndex = gIndex + 1
    pins.pin.append(pin)

# define vu13p board information
vu13p = Board(display_name="Virtex UltraScale+ VU13P Accelerator Board", name="vu13p", url=URL, schema_version="2.2", vendor=COMPANY_NAME, preset_file="preset.xml", description = "Virtex UltraScale+ VU13P Accelerator Board")
vu13p.images = Images( [Image(name="vu13p.jpeg", display_name="vu13p Board", sub_type="board")] )
vu13p.compatible_board_revisions = CompatibleBoardRevisions( [Revision(value = "1.0", id = "0")] )
vu13p.file_version = FILE_VERSION
vu13p.jumpers = Jumpers()

part0 = Component(name="part0", display_name="Virtex UltraScale+ VU13P Accelerator Board", type=ComponentType.FPGA, part_name="xcvu13p-fhgb2104-2-i", pin_map_file="part0_pins.xml", vendor=COMPANY_NAME)
vu13p.components = Components([part0])

part0.description = "Virtex-UltraScale+ FPGA part on the board"
part0.interfaces = Interfaces()

def no_reverse(name):
    return name

def reverse_name_pn(name):
    # if name endswith p/n reverse it to n/p
    if name.endswith('p') or name.endswith('n'):
        return name[:-1] + ('p' if name.endswith('n') else 'n')
    return name

def reverse_name_tc(name):
    # if name ends with t/c reverse it to c/t
    if name.endswith('t') or name.endswith('c'):
        return name[:-1] + ('t' if name.endswith('c') else 'c')
    return name

def map_xdc_ports(logical_port, physical_port, portname_xdc, direction, ports_data, iostd_data, reverse=no_reverse, lanelimit=None):
    component_port = reverse(portname_xdc)
    port_map = PortMap(logical_port = logical_port, physical_port = physical_port, dir = PortMapDir(direction))
    port_map.pin_maps = PinMaps()
    pin_data = ports_data[portname_xdc]
    reverse_pin = lambda x:x
    if reverse != no_reverse:
        reverse_pin = get_diffpair
    pin_len = len(pin_data)
    if lanelimit and pin_len > lanelimit:
        pin_len = lanelimit
    if len(pin_data) <= 1:
        pin_map = PinMap()
        pin_map.port_index = '0'
        pin_map.component_pin = component_port
        port_map.pin_maps.pin_map.append(pin_map)
        if portname_xdc in iostd_data:
            add_pin(component_port, reverse_pin(pin_data[0]), iostd_data[portname_xdc])
        else:
            add_pin(component_port, reverse_pin(pin_data[0]))
    else:
        port_map.left = "0"
        port_map.right = str(pin_len - 1)
        for ind, pin in pin_data.items():
            if ind >= pin_len:
                break
            pin_map = PinMap()
            pin_map.port_index = str(ind)
            pin_map.component_pin = component_port + str(ind)
            port_map.pin_maps.pin_map.append(pin_map)
            if portname_xdc in iostd_data:
                add_pin(pin_map.component_pin, reverse_pin(pin), iostd_data[portname_xdc])
            else:
                add_pin(pin_map.component_pin, reverse_pin(pin))
    return port_map

# sdram interface
ddrpins = [{}, {}, {}, {}]
ddrclkpins = [{}, {}, {}, {}]
for i in range(0, 4):
    ddrpins[i]['c1_st_index'] = str(gIndex)
    ddr = Interface(mode=InterfaceMode.MASTER, name=f"ddr4_sdram_c{i}_083", type="xilinx.com:interface:ddr4_rtl:1.0", of_component=f"ddr4_sdram_c{i}", preset_proc="ddr4_sdram_preset_083")
    part0.interfaces.interface.append(ddr)

    ddr.description = "DDR4 board interface, it can use DDR4 IP for connection. "
    ddr.preferred_ips = PreferredIps([PreferredIp(vendor="xilinx.com", library="ip", name="ddr4", order="0")])

    ddr.port_maps = PortMaps()
    ports = {'ACT_N': 'out', 'ADR': 'out', 'BA': 'out', 'BG': 'out', 'CK_T': 'out', 'CKE': 'out', 'CS_N': 'out', 'DM_N': 'inout', 'DQ': 'inout', 'DQS_T': 'inout', 'ODT': 'out', 'RESET_N': 'out'}
    port_maps = {}
    ports_data = xdcs[f'ddr4_c{i}']['ports']
    iostd_data = xdcs[f'ddr4_c{i}']['iostd']
    for logical_port, direction in ports.items():
        lower_port = logical_port.lower()
        physical_port = f'c{i}_ddr4_{lower_port}'
        port_maps[logical_port] = map_xdc_ports(logical_port, physical_port, physical_port, direction, ports_data, iostd_data)
        ddr.port_maps.port_map.append(port_maps[logical_port])
    # map diff pair
    diffs = [('CK_T', 'CK_C', 'out', reverse_name_tc), ('DQS_T', 'DQS_C', 'inout', reverse_name_tc)]
    for org_port, new_port, direction, rev in diffs:
        lower_port = org_port.lower()
        physical_port = f'c{i}_ddr4_{lower_port}'
        port_maps[new_port] = map_xdc_ports(new_port, physical_port, physical_port, direction, ports_data,  iostd_data, rev)
        ddr.port_maps.port_map.append(port_maps[new_port])

    part0.interfaces.interface.append(ddr)

    ddrpins[i]['c1_end_index'] = str(gIndex - 1)
    ddrclkpins[i]['c1_st_index'] = str(gIndex)
    # ddr clock @ 400mhz
    ddr_clk = Interface(mode=InterfaceMode.SLAVE, name=f"ddr4_sdram_c{i}_sys_clk", type="xilinx.com:interface:diff_clock_rtl:1.0", of_component=f"ddr4_sdram_c{i}_sys_clk", preset_proc="ddr4_sdram_clk_preset")
    part0.interfaces.interface.append(ddr_clk)
    ddr_clk.parameters = Parameters([Parameter(name="frequency", value="400000000")])
    ddr_clk.preferred_ips = PreferredIps([PreferredIp(vendor="xilinx.com", library="ip", name="util_ds_buf", order="0")])
    ddr_clk.port_maps = PortMaps()
    ddr_clk.port_maps.port_map.append(
        map_xdc_ports('CLK_P', f"c{i}_sys_clk_p", f"c{i}_sys_clk_p", 'in', ports_data, iostd_data),
    )
    ddr_clk.port_maps.port_map.append(
        map_xdc_ports('CLK_N', f"c{i}_sys_clk_n", f"c{i}_sys_clk_p", 'in', ports_data, iostd_data, reverse_name_pn),
    )
    ddrclkpins[i]['c1_end_index'] = str(gIndex - 1)

# pcie interface

pcie_ports_data = xdcs['pcie']['ports']
pcie_iostd_data = xdcs['pcie']['iostd']
pcie_ports_datarx = gen_rx_databasse(xdcs['pcie']['ports'])

# pcie pins
pcie_pins = {
    'clock': {},
    'reset': {},
    "lane": {},
}

# clock

pcie_pins['clock']['c1_st_index'] = str(gIndex)

pcie_refclk = Interface(mode=InterfaceMode.SLAVE, name="pcie_refclk", type="xilinx.com:interface:diff_clock_rtl:1.0", of_component="pcie_refclk", preset_proc="pcie_refclk_preset")
part0.interfaces.interface.append(pcie_refclk)
pcie_refclk.parameters = Parameters([Parameter(name="frequency", value="100000000")])
pcie_refclk.preferred_ips = PreferredIps([PreferredIp(vendor="xilinx.com", library="ip", name="util_ds_buf", order="0")])
pcie_refclk.port_maps = PortMaps()

pcie_refclk.port_maps.port_map.append(map_xdc_ports("CLK_P", "pcie_mgt_clkp", "pcie_clk_clk_p", "in", pcie_ports_data, pcie_iostd_data))
pcie_refclk.port_maps.port_map.append(map_xdc_ports("CLK_N", "pcie_mgt_clkn", "pcie_clk_clk_p", "in", pcie_ports_data, pcie_iostd_data, reverse_name_pn))

pcie_pins['clock']['c1_end_index'] = str(gIndex - 1)

# lanes
pcie_lanes = [2**i for i in range(5)]

# x16 pcie interface @ X0Y1

pcie_pins['lane']['c1_st_index'] = str(gIndex)

for lane in pcie_lanes:
    pcieXN = Interface(mode=InterfaceMode.MASTER, name=f"pci_express_x{lane}", type="xilinx.com:interface:pcie_7x_mgt_rtl:1.0", of_component="pci_express", preset_proc=f"pciex{lane}_preset")
    part0.interfaces.interface.append(pcieXN)
    pcieXN.preferred_ips = PreferredIps([
        PreferredIp(vendor="xilinx.com", library="ip", name="xdma", order="0"),
        PreferredIp(vendor="xilinx.com", library="ip", name="qdma", order="1"),
        PreferredIp(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", order="2"),    
    ])

    pcieXN.port_maps = PortMaps()

    pcieXN.port_maps.port_map.append(map_xdc_ports("txp", "pcie_tx0_px16", "pcie_lane_txp", "out", pcie_ports_data, pcie_iostd_data, lanelimit=lane))
    pcieXN.port_maps.port_map.append(map_xdc_ports("txn", "pcie_tx0_nx16", "pcie_lane_txp", "out", pcie_ports_data, pcie_iostd_data, reverse_name_pn, lanelimit=lane))

    pcieXN.port_maps.port_map.append(map_xdc_ports("rxp", "pcie_rx0_px16", "pcie_lane_rxp", "out", pcie_ports_datarx, pcie_iostd_data, lanelimit=lane))
    pcieXN.port_maps.port_map.append(map_xdc_ports("rxn", "pcie_rx0_nx16", "pcie_lane_rxp", "out", pcie_ports_datarx, pcie_iostd_data, reverse_name_pn, lanelimit=lane))

    pcieXN.parameters = Parameters([Parameter(name="block_location", value="X0Y1")])

pcie_pins['lane']['c1_end_index'] = str(gIndex - 1)

# reset

pcie_pins['reset']['c1_st_index'] = str(gIndex)

pcie_reset = Interface(mode=InterfaceMode.SLAVE, name="pcie_perstn", type="xilinx.com:signal:reset_rtl:1.0", of_component="pci_express")
part0.interfaces.interface.append(pcie_reset)
pcie_reset.preferred_ips = PreferredIps([
    PreferredIp(vendor="xilinx.com", library="ip", name="xdma", order="0"),
    PreferredIp(vendor="xilinx.com", library="ip", name="qdma", order="1"),
    PreferredIp(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", order="2"),
])

pcie_reset.port_maps = PortMaps()
pcie_reset.port_maps.port_map.append(map_xdc_ports("RST", "pcie_perstn_rst", "pcie_reset", "in", pcie_ports_data, pcie_iostd_data))

pcie_reset.parameters = Parameters([
    Parameter(name="rst_polarity", value="0"),
    Parameter(name="type", value="PCIE_PERST"),
])

pcie_pins['reset']['c1_end_index'] = str(gIndex - 1)

# system

system_ports_data = xdcs['sysytem']['ports']
system_iostd_data = xdcs['sysytem']['iostd']

## system clock

clkpin = {}
clkpin['c1_st_index'] = str(gIndex)

clk = Interface(mode=InterfaceMode.SLAVE, name="default_sysclk1_100", type="xilinx.com:interface:diff_clock_rtl:1.0", of_component="default_sysclk1_100", preset_proc="default_sysclk1_100_preset")
part0.interfaces.interface.append(clk)
clk.parameters = Parameters([Parameter(name="frequency", value="100000000")])
clk.preferred_ips = PreferredIps([
    PreferredIp(vendor="xilinx.com", library="ip", name="clk_wiz", order="0"),
    PreferredIp(vendor="xilinx.com", library="ip", name="util_ds_buf", order="0")
])

clk.port_maps = PortMaps([
    map_xdc_ports("CLK_P", "sysclk1_100_p", "system_clk_p", "in", system_ports_data, system_iostd_data),
    map_xdc_ports("CLK_N", "sysclk1_100_n", "system_clk_p", "in", system_ports_data, system_iostd_data, reverse_name_pn)
])
clkpin["c1_end_index"] = str(gIndex - 1)

# qfp interface

qsfp_portnames = {
    "qsfp1": {
        "txp": [("c2c_master_tx_txp", 2, range(0, 2)), ("c2c_slave_tx_txp", 2, range(2, 4))],
        "rxp": [("c2c_master_rx_rxp", 2, range(0, 2)), ("c2c_slave_rx_rxp", 2, range(2, 4))],
        "txn": [("c2c_master_tx_txn", 2, range(0, 2)), ("c2c_slave_tx_txn", 2, range(2, 4))],
        "rxn": [("c2c_master_rx_rxn", 2, range(0, 2)), ("c2c_slave_rx_rxn", 2, range(2, 4))],
        "clkp": "up_qsfp161_clk_p",
        "clkn": "up_qsfp161_clk_n",
        "i2c_sda": "up_qsfp_i2c_sda",
        "i2c_scl": "up_qsfp_i2c_scl",
    },
    "qsfp2": {
        "txp": [("dn_qsfp{idx}_tx_p", 4, range(0, 4))],
        "rxp": [("dn_qsfp{idx}_rx_p", 4, range(0, 4))],
        "txn": [("dn_qsfp{idx}_tx_n", 4, range(0, 4))],
        "rxn": [("dn_qsfp{idx}_rx_n", 4, range(0, 4))],
        "clkp": "dn_qsfp161_clk_p",
        "clkn": "dn_qsfp161_clk_n",
        "i2c_sda": "dn_qsfp_i2c_sda",
        "i2c_scl": "dn_qsfp_i2c_scl",
    }
}

qsfp_ports_data = xdcs['vu13p_qsfp']['ports']
qsfp_iostd_data = xdcs['vu13p_qsfp']['iostd']

new_qsfp_ports_data = {}
new_qsfp_iostd_data = {}

for component_name, portdata in qsfp_portnames.items():
    for port in ("txp", "rxp", "txn", "rxn"):
        # rename ports_data
        new_port = f"{component_name}_{port}"
        new_qsfp_ports_data[new_port] = {}
        for oldname, sz, oldrange in portdata[port]:
            for old_idx, new_idx in zip(range(0, sz), oldrange):
                mapoldname = oldname.format(idx=old_idx)
                if mapoldname != oldname:
                    new_qsfp_ports_data[new_port][new_idx] = qsfp_ports_data[mapoldname][0]
                else:
                    new_qsfp_ports_data[new_port][new_idx] = qsfp_ports_data[mapoldname][old_idx]
    for port in ("clkp", "clkn", "i2c_sda", "i2c_scl"):
        new_qsfp_ports_data[f"{component_name}_{port}"] = qsfp_ports_data[portdata[port]]
        if portdata[port] in qsfp_iostd_data:
            new_qsfp_iostd_data[f"{component_name}_{port}"] = qsfp_iostd_data[portdata[port]]

def g_name(port):
    # tuen xxp to GXX_p
    return ("g" + port[:-1] + "_" + port[-1]).upper()

qsfp_pins = {
    "qsfp1": {},
    "qsfp2": {}
}

qsfp_clk_pins = {
    "qsfp1": {},
    "qsfp2": {}
}

def qsfp_preferip(lane):
    if lane % 2 == 0:
        preferred_ips = PreferredIps([
            PreferredIp(vendor="xilinx.com", library="ip", name="xxv_ethernet", order="0"),
            PreferredIp(vendor="xilinx.com", library="ip", name="l_ethernet", order="0"),
            PreferredIp(vendor="xilinx.com", library="ip", name="interlaken", order="1")
        ])
        if lane == 4:
            preferred_ips.preferred_ip.append(
                PreferredIp(vendor="xilinx.com", library="ip", name="cmac_usplus", order="0")
            )
    else:
        preferred_ips = PreferredIps([
            PreferredIp(vendor="xilinx.com", library="ip", name="xxv_ethernet", order="0"),
            PreferredIp(vendor="xilinx.com", library="ip", name="interlaken", order="1")
        ])
    return preferred_ips

def qsfp_ipname(lane):
    preferredips = qsfp_preferip(lane)
    ipname = [ip.name for ip in preferredips.preferred_ip]
    return ipname

def filter_ip(lane, iplist: List[Ip]):
    ipname = qsfp_ipname(lane)
    return [ip for ip in iplist if ip.name in ipname]

for component_name, _ in qsfp_portnames.items():
    qsfp_pins[component_name]['c1_st_index'] = str(gIndex)
    for lane in range(1, 5):
        interface_name = f"{component_name}_{lane}x"
        qsfp_interface = Interface(mode=InterfaceMode.MASTER, name=interface_name, type="xilinx.com:interface:gt_rtl:1.0", of_component=component_name, preset_proc=f"{interface_name}_preset")
        part0.interfaces.interface.append(qsfp_interface)
        qsfp_interface.description = f"{lane}-lane GT interface over QSFP"
        qsfp_interface.preferred_ips = qsfp_preferip(lane)

        port_maps = PortMaps()
        qsfp_interface.port_maps = port_maps
        for port, direction in [("txp", "out"), ("rxp", "in"), ("txn", "out"), ("rxn", "in")]:
            port_maps.port_map.append(
                map_xdc_ports(logical_port=g_name(port), physical_port=f"{component_name}_{port}{lane}", portname_xdc=f"{component_name}_{port}", direction=direction, ports_data=new_qsfp_ports_data, iostd_data=new_qsfp_iostd_data, lanelimit=lane)
            )
    qsfp_pins[component_name]['c1_end_index'] = str(gIndex - 1)

    qsfp_clk_pins[component_name]['c1_st_index'] = str(gIndex)

    # clk interface name
    qclk_interface_name = f"{component_name}_eeg2102_clk"
    # 161.132M
    clk_interface = Interface(mode=InterfaceMode.SLAVE, name=qclk_interface_name, type="xilinx.com:interface:diff_clock_rtl:1.0", of_component=component_name)
    part0.interfaces.interface.append(clk_interface)
    clk_interface.parameters = Parameters([Parameter(name="frequency", value="161132000")])
    clk_interface.preferred_ips = PreferredIps([
        PreferredIp(vendor="xilinx.com", library="ip", name="xxv_ethernet", order="0"),
        PreferredIp(vendor="xilinx.com", library="ip", name="l_ethernet", order="1"),
        PreferredIp(vendor="xilinx.com", library="ip", name="interlaken", order="2"),
        PreferredIp(vendor="xilinx.com", library="ip", name="cmac_usplus", order="3"),
    ])
    port_maps = PortMaps()
    clk_interface.port_maps = port_maps
    port_maps.port_map.append(map_xdc_ports("CLK_P", qclk_interface_name + "_p", f"{component_name}_clkp", "in", new_qsfp_ports_data, new_qsfp_iostd_data))
    port_maps.port_map.append(map_xdc_ports("CLK_N", qclk_interface_name + "_p", f"{component_name}_clkn", "in", new_qsfp_ports_data, new_qsfp_iostd_data))
    qsfp_clk_pins[component_name]['c1_end_index'] = str(gIndex)
    # TODO: I2C??



# Components and connections
## SDRAM
for i in range(0, 4):
    component_ddr = Component(
        name=f"ddr4_sdram_c{i}", 
        display_name=f"DDR4 SDRAM C{i}", 
        type=ComponentType.CHIP, sub_type="ddr", 
        major_group="External Memory", 
        part_name="MT40A512M16HA-083E",
        vendor="Micron", spec_url="https://media-www.micron.com/-/media/client/global/documents/products/data-sheet/dram/ddr4/8gb_ddr4_sdram.pdf")
    vu13p.components.component.append(component_ddr)
    component_ddr.parameters = Parameters([
        Parameter(name="ddr_type", value="ddr4"),
        Parameter(name="size", value="4GB"),
    ])
    component_ddr.component_modes = ComponentModes([
        ComponentMode(name=f"ddr4_sdram_c{i}_083", display_name=f"ddr4_sdram_c{i}_083", description="Default mode",
                        interfaces=Interfaces([
                            Interface(name=f"ddr4_sdram_c{i}_083"),
                            Interface(name=f"ddr4_sdram_c{i}_sys_clk", optional=InterfaceOptional.TRUE)
                        ])),
    ])
    ### ddr clk (Si591?)
    component_ddrclk = Component(name=f"ddr4_sdram_c{i}_sys_clk", display_name=f"400Mhz differential clock{i}", 
                                 type=ComponentType.CHIP, sub_type="system_clock", 
                                 major_group="Clock Sources", part_name="Si591?", vendor="Si Time", spec_url="www.sitime.com",
                                 parameters=Parameters([Parameter(name="frequency", value="400000000")]),
                                 description="400MHz System clock for the design used by SDRAM"
                                )

## sysclk
component_sysclk = Component(
    name="default_sysclk1_100",
    display_name="Default Sysclk1 100",
    type=ComponentType.CHIP, sub_type="system_clock",
    major_group="Clock Sources",
    part_name="Unknown Clock", vendor="Si Time",spec_url="www.sitime.com",
    description="100MHz System clock for the design",
    parameters=Parameters([Parameter(name="frequency", value="100000000")]),
)

vu13p.components.component.append(component_sysclk)

## pci_express
component_pcie = Component(
    name="pci_express",
    display_name="PCI Express",
    type=ComponentType.CHIP, sub_type="chip",
    major_group="Miscellaneous", description="PCI Express")
vu13p.components.component.append(component_pcie)
component_pcie.component_modes = ComponentModes([
    ComponentMode(name=f"pci_express_x{lane}", display_name="pci_express x16",
        interfaces = Interfaces([
            Interface(name=f"pci_express_x{lane}"),
            Interface(name="pcie_perstn", optional=InterfaceOptional.TRUE),
            Interface(name="pcie_refclk", optional=InterfaceOptional.TRUE),
        ]),
        preferred_ips = PreferredIps([
            PreferredIp(vendor="xilinx.com", library="ip", name="xdma", order="0"),
            PreferredIp(vendor="xilinx.com", library="ip", name="qdma", order="1"),
            PreferredIp(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", order="2"),
        ]))
for lane in pcie_lanes])

## qsfp

for component_id in (1, 2):
    component_name = f"qsfp{component_id}"
    component_qsfp = Component(
        name=component_name,
        type=ComponentType.CHIP, sub_type="sfp", major_group="Ethernet Configurations", part_name="Unknown", vendor="Unknown", spec_url="www.marvell.com",
        display_name=f"QSFP Connector {component_id}",
        description=f"QSFP Connector {component_id}",
    )
    vu13p.components.component.append(component_qsfp)
    component_qsfp.component_modes = ComponentModes()
    for lane in range(1, 5):
        mode_name = f"qsfp{component_id}_{lane}x"
        mode = ComponentMode(name=mode_name, display_name=mode_name)
        qclk_interface_name = f"{component_name}_eeg2102_clk"
        mode.interfaces = Interfaces([
            Interface(name=mode_name),
            Interface(name=qclk_interface_name, optional=InterfaceOptional.TRUE),
        ])
        mode.preferred_ips = qsfp_preferip(lane)

## jtag_chains
vu13p.jtag_chains = JtagChains(
    JtagChain(name="chain1", position=Position(name="0", component="part0"))
)

## connections
def mdd(pin):
    return str(int(pin['c1_end_index']) - int(pin['c1_st_index']))

vu13p.connections = Connections([
    Connection(name=f"part0_ddr4_sdram_c{i}", component1=ConnectionComponent1.PART0, component2=f"ddr4_sdram_c{i}",
    connection_map=[ConnectionMap(
        name=f"part0_ddr4_sdram_c{i}",
        c1_st_index=ddrpins[i]['c1_st_index'],
        c1_end_index=ddrpins[i]['c1_end_index'],
        c2_st_index="0",
        c2_end_index=mdd(ddrpins[i]),
    )]) for i in range(0, 4)] + [
    Connection(name =f"part0_ddr4_sdram_c{i}_sys_clk", component1=ConnectionComponent1.PART0, component2=f"ddr4_sdram_c{i}_sys_clk",
        connection_map=[ConnectionMap(
            name=f"part0_ddr4_sdram_c{i}_sys_clk",
            c1_st_index=ddrclkpins[i]['c1_st_index'],
            c1_end_index=ddrclkpins[i]['c1_end_index'],
            c2_st_index="0",
            c2_end_index="1")]
    ) for i in range(0, 4)
    ] + 
    [Connection(name="part0_default_sysclk1_100", component1=ConnectionComponent1.PART0, component2="default_sysclk1_100",
        connection_map=[ConnectionMap(
            name="part0_default_sysclk1_100",
            c1_st_index=clkpin['c1_st_index'],
            c1_end_index=clkpin['c1_end_index'],
            c2_st_index="0",
            c2_end_index="1")]
    )] + 
    [Connection(name=f"part0_qsfp{component_id}_gt", component1=ConnectionComponent1.PART0, component2=f"qsfp{component_id}", connection_map=[
        ConnectionMap(name=f"part0_qsfp{component_id}", c1_st_index=qsfp_pins[f"qsfp{component_id}"]['c1_st_index'], c1_end_index=qsfp_pins[f"qsfp{component_id}"]['c1_end_index'], c2_st_index="0", c2_end_index=mdd(qsfp_pins[f"qsfp{component_id}"]))
    ]) for component_id in (1, 2)] + 
    [Connection(name=f"part0_qsfp{component_id}_eeg2102_clk", component1=ConnectionComponent1.PART0, component2=f"qsfp{component_id}_eeg2102_clk", connection_map=[
        ConnectionMap(name=f"part0_qsfp{component_id}_eeg2102_clk", c1_st_index=qsfp_clk_pins[f"qsfp{component_id}"]['c1_st_index'], c1_end_index=qsfp_clk_pins[f"qsfp{component_id}"]['c1_end_index'], c2_st_index="0", c2_end_index=mdd(qsfp_clk_pins[f"qsfp{component_id}"]))
    ]) for component_id in (1, 2)] + 
    # pcie
    [
        Connection(name=f"part0_pci_express", component1=ConnectionComponent1.PART0, component2=f"pci_express", connection_map=[
            ConnectionMap(name=f"part0_pci_express", c1_st_index=pcie_pins["lane"]['c1_st_index'], c1_end_index=pcie_pins["lane"]['c1_end_index'], c2_st_index="0", c2_end_index=mdd(pcie_pins["lane"]))
        ]),
        # part0_pcie_perstn
        Connection(name=f"part0_pcie_perstn", component1=ConnectionComponent1.PART0, component2=f"pcie_perstn", connection_map=[
            ConnectionMap(name=f"part0_pcie_perstn", c1_st_index=pcie_pins["reset"]['c1_st_index'], c1_end_index=pcie_pins["reset"]['c1_end_index'], c2_st_index="0", c2_end_index=mdd(pcie_pins["reset"]))
        ]),
        # part0_pcie_refclk
        Connection(name=f"part0_pcie_refclk", component1=ConnectionComponent1.PART0, component2=f"pcie_refclk", connection_map=[
            ConnectionMap(name=f"part0_pcie_refclk", c1_st_index=pcie_pins["clock"]['c1_st_index'], c1_end_index=pcie_pins["clock"]['c1_end_index'], c2_st_index="0", c2_end_index=mdd(pcie_pins["clock"]))
        ]),
    ]
)

# ip associated rule
ip_associated_rules = IpAssociatedRules()
vu13p.ip_associated_rules = ip_associated_rules
ip_associated_rule = IpAssociatedRule(name="default")
ip_associated_rules.ip_associated_rule = ip_associated_rule

ip_associated_rule.ip.append(
    B.Ip(vendor="xilinx.com", library="ip", name="ddr4", version="*", ip_interface="C0_SYS_CLK",
         associated_board_interfaces = [AssociatedBoardInterfaces([
            AssociatedBoardInterface(name=f"ddr4_sdram_c{i}_sys_clk", order=f"{i}")
         for i in range(0, 4) ])]
    )
)

ip_associated_rule.ip.extend([
    B.Ip(vendor="xilinx.com", library="ip", name=ipname, version="*", ip_interface="sys_rst_n",
        associated_board_interfaces=[AssociatedBoardInterfaces([
            AssociatedBoardInterface(name="pcie_perstn", order="0"),
        ])]
    )
for ipname in ["qdma", "xdma", "pcie4_uscale_plus"]])


ifclks = ["default_sysclk1_100", "pcie_refclk"] + [f"ddr4_sdram_c{i}_sys_clk" for i in range(0, 4)]
ip_associated_rule.ip.extend([
    B.Ip(vendor="xilinx.com", library="ip", name="util_ds_buf", version="*", ip_interface="CLK_IN_D",
        associated_board_interfaces=[AssociatedBoardInterfaces([
            AssociatedBoardInterface(name=ifname, order=str(idx))
        for idx, ifname in enumerate(ifclks) ]) ]
    )])

# gt_serial_port
gtIps = (
    "xxv_ethernet", "interlaken", "l_ethernet", "cmac_usplus"
)
for ip in gtIps:
    ipLane = list(filter(lambda lane:ip in qsfp_ipname(lane), range(1, 5)))
    order = 0
    ip_associated_rule.ip.append(
        B.Ip(vendor="xilinx.com", library="ip", name=ip, version="*", ip_interface="gt_serial_port",
            associated_board_interfaces=[AssociatedBoardInterfaces([
                AssociatedBoardInterface(name=f"qsfp{component_id}_{lane}x", order=f"{(order:=order+1)-1}")
            for component_id in (1, 2) for lane in ipLane])]
        )
    )
    order = 0
    ip_associated_rule.ip.append(
        B.Ip(vendor="xilinx.com", library="ip", name=ip, version="*", ip_interface="gt_ref_clk",
            associated_board_interfaces=[AssociatedBoardInterfaces([
                AssociatedBoardInterface(name=f"qsfp{component_id}_eeg2102_clk", order=f"{(order:=order+1)-1}")
            for component_id in (1, 2) ])]
        )
    )

# system configuration

ipPresets = IpPresets(schema="1.0")
ipPresets.ip_preset = [
    IpPreset(preset_proc_name="pcie_refclk_preset", ip = [
        Ip(vendor="xilinx.com", library="ip", name="util_ds_buf", user_parameters = UserParameters([
            UserParameter(name="CONFIG.C_BUF_TYPE", value="IBUFDSGTE"),
            UserParameter(name="CONFIG.C_SIZE", value="1"),
        ])),
    ]),
    IpPreset(preset_proc_name="ddr4_sdram_preset_083", ip = [
        Ip(vendor="xilinx.com", library="ip", name="ddr4", user_parameters = UserParameters([
            UserParameter(name="CONFIG.C0.DDR4_MemoryPart", value="MT40A512M16HA-083E"),
            UserParameter(name="CONFIG.C0.DDR4_TimePeriod", value="833"),
            UserParameter(name="CONFIG.C0.DDR4_InputClockPeriod", value="2499"),
            UserParameter(name="CONFIG.C0.DDR4_AxiAddressWidth", value="31"),
            UserParameter(name="CONFIG.System_Clock", value="Differential"),
            UserParameter(name="CONFIG.C0.DDR4_DataWidth", value="72"),
            UserParameter(name="CONFIG.C0.DDR4_AxiDataWidth", value="512"),
            UserParameter(name="CONFIG.ADDN_UI_CLKOUT1_FREQ_HZ", value="100"),
        ])),
    ]),
    IpPreset(preset_proc_name="default_sysclk1_100_preset", ip = [
        Ip(vendor="xilinx.com", library="ip", name="clk_wiz", ip_interface="CLK_IN1_D", user_parameters = UserParameters([
            UserParameter(name="CONFIG.PRIM_IN_FREQ", value="100"),
            UserParameter(name="CONFIG.PRIM_SOURCE", value="Differential_clock_capable_pin"),
        ])),
        Ip(vendor="xilinx.com", library="ip", name="util_ds_buf", user_parameters = UserParameters([
            UserParameter(name="CONFIG.C_BUF_TYPE", value="IBUFDS"),
            UserParameter(name="CONFIG.C_SIZE", value="1"),
        ])),
    ]),
    IpPreset(preset_proc_name="ddr4_sdram_clk_preset", ip = [
        Ip(vendor="xilinx.com", library="ip", name="util_ds_buf", user_parameters = UserParameters([
            UserParameter(name="CONFIG.C_BUF_TYPE", value="IBUFDS"),
            UserParameter(name="CONFIG.C_SIZE", value="1"),
        ])),
    ]),
] + [
# pciex16_preset
    IpPreset(preset_proc_name=f"pciex{lane}_preset", ip = [
        Ip(vendor="xilinx.com", library="ip", name="xdma", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value=f"X{lane}"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
        ])),
        Ip(vendor="xilinx.com", library="ip", name="qdma", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_speed", value="8.0_GT/s"),
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value=f"X{lane}"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
        ])),
        Ip(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value=f"X{lane}"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
        ])),
    ]) for lane in pcie_lanes
]


gt_quad = {
    "qsfp1": list(range(52, 55 + 1)), # 233
    "qsfp2": list(range(36, 39 + 1)), # 229
}

def gt_selection(comp, lane):
    quad = gt_quad[comp]
    st = quad[0]
    if lane == 1:
        return f"X1Y{st}"
    ed = quad[lane - 1]
    return f"X1Y{st}~X1Y{ed}"

def quad_group(comp, _):
    quad = gt_quad[comp]
    st = quad[0]
    return f"Quad_X1Y{st}"

ilkne_selection = {
    "qsfp1": "ILKNE4_X1Y7",
    "qsfp2": "ILKNE4_X1Y5",
}

cmac_selection = {
    "qsfp1": "CMACE4_X0Y11",
    "qsfp2": "CMACE4_X0Y7",
}

for component_name in ("qsfp1", "qsfp2"):
    for lane in range(1, 5):
        preset_proc_name = f"{component_name}_{lane}x_preset"
        ip_preset = IpPreset(preset_proc_name=preset_proc_name)
        ipPresets.ip_preset.append(ip_preset)
        ip_preset.ip = filter_ip(lane, [
            Ip(vendor="xilinx.com", library="ip", name="xxv_ethernet", user_parameters = UserParameters([
                UserParameter(name = "CONFIG.LINE_RATE", value = "10"), #
                UserParameter(name = "CONFIG.GT_REF_CLK_FREQ", value = "161.132"), #
                UserParameter(name = "CONFIG.NUM_OF_CORES", value = str(lane)),
                UserParameter(name = "CONFIG.GT_TYPE", value = "GTY"),
                UserParameter(name = "CONFIG.GT_GROUP_SELECT", value = quad_group(component_name, lane))
            ])),
            Ip(vendor="xilinx.com", library="ip", name="l_ethernet", user_parameters = UserParameters([
                UserParameter(name = "CONFIG.LINE_RATE", value = "40"), #
                UserParameter(name = "CONFIG.GT_REF_CLK_FREQ", value = "161.132"), #
                UserParameter(name = "CONFIG.GT_TYPE", value = "GTY"),
                UserParameter(name = "CONFIG.GT_GROUP_SELECT", value = quad_group(component_name, lane))
            ])),
            Ip(vendor="xilinx.com", library="ip", name="interlaken", user_parameters = UserParameters([
                UserParameter(name = "CONFIG.LINE_RATE", value = "10.3125"), #
                UserParameter(name = "CONFIG.GT_REF_CLK_FREQ", value = "161.1328125"), # 
                UserParameter(name = "CONFIG.NUM_LANES", value = str(lane)),
                UserParameter(name = "CONFIG.GT_TYPE", value = "GTY"),
                UserParameter(name = "CONFIG.GT_SELECT", value = gt_selection(component_name, lane)),
                UserParameter(name = "CONFIG.ILKN_CORE_LOC", value = "ILKNE4_X1Y8")
            ])),
            Ip(vendor="xilinx.com", library="ip", name="cmac_usplus", user_parameters = UserParameters([
                UserParameter(name = "CONFIG.GT_TYPE", value = "GTY"),
                UserParameter(name = "CONFIG.CMAC_CAUI4_MODE", value = "1"),
                UserParameter(name = "CONFIG.NUM_LANES", value = f"{lane}x25"), #
                UserParameter(name = "CONFIG.GT_REF_CLK_FREQ", value = "161.1328125"), #
                UserParameter(name = "CONFIG.CMAC_CORE_SELECT", value = cmac_selection[component_name]),
                UserParameter(name = "CONFIG.GT_GROUP_SELECT", value = gt_selection(component_name, lane)),
                UserParameter(name = "CONFIG.RS_FEC_TRANSCODE_BYPASS", value = "0"),
            ])),
        ])

# Save to xml
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.formats.dataclass.serializers import XmlSerializer

config = SerializerConfig(pretty_print=True)
serializer = XmlSerializer(config=config)

with open("result/Acompany/vu13p/1.0/part0_pins.xml", "w") as f:
    f.write(serializer.render(part_info))

with open("result/Acompany/vu13p/1.0/board.xml", "w") as f:
    f.write(serializer.render(vu13p))

with open("result/Acompany/vu13p/1.0/presets.xml", "w") as f:
    f.write(serializer.render(ipPresets))

# copy board image file to result
import shutil
shutil.copyfile("img/IMG_0001.jpg", "result/Acompany/vu13p/1.0/vu13p.jpeg")

# generate xitem file
from xml.dom import minidom
xmldoc = minidom.parse("result/Acompany/vu13p/1.0/board.xml")
from generate_xitem_json import createXitemJson
createXitemJson(xmldoc, "result/Acompany/vu13p/1.0/xitem.json")