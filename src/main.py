import os
from pathlib import Path
import sys
from xdc import parse_xdc

COMPANY_NAME = "A company"
# override company name with environment variable
if "COMPANY_NAME" in os.environ:
    COMPANY_NAME = os.environ["COMPANY_NAME"]

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
vu13p = Board(display_name="Virtex UltraScale+ VU13P Accelerator Board", name="vu13p", url="http://", schema_version="2.2", vendor=COMPANY_NAME, preset_file="preset.xml", description = "Virtex UltraScale+ VU13P Accelerator Board")
vu13p.images = Images( [Image(name="vu13p.jpeg", display_name="vu13p Board", sub_type="board")] )
vu13p.compatible_board_revisions = CompatibleBoardRevisions( [Revision(value = "1.0", id = "0")] )
vu13p.file_version = "1.0"
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

def map_xdc_ports(logical_port, physical_port, portname_xdc, direction, ports_data, iostd_data, reverse=no_reverse):
    component_port = reverse(portname_xdc)
    port_map = PortMap(logical_port = logical_port, physical_port = physical_port, dir = PortMapDir(direction))
    port_map.pin_maps = PinMaps()
    pin_data = ports_data[portname_xdc]
    reverse_pin = lambda x:x
    if reverse != no_reverse:
        reverse_pin = get_diffpair
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
        port_map.right = str(len(pin_data) - 1)
        for ind, pin in pin_data.items():
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

# clock

pcie_refclk = Interface(mode=InterfaceMode.SLAVE, name="pcie_refclk", type="xilinx.com:interface:diff_clock_rtl:1.0", of_component="pcie_refclk", preset_proc="pcie_refclk_preset")
part0.interfaces.interface.append(pcie_refclk)
pcie_refclk.parameters = Parameters([Parameter(name="frequency", value="100000000")])
pcie_refclk.preferred_ips = PreferredIps([PreferredIp(vendor="xilinx.com", library="ip", name="util_ds_buf", order="0")])
pcie_refclk.port_maps = PortMaps()

pcie_refclk.port_maps.port_map.append(map_xdc_ports("CLK_P", "pcie_mgt_clkp", "pcie_clk_clk_p", "in", pcie_ports_data, pcie_iostd_data))
pcie_refclk.port_maps.port_map.append(map_xdc_ports("CLK_N", "pcie_mgt_clkn", "pcie_clk_clk_p", "in", pcie_ports_data, pcie_iostd_data, reverse_name_pn))

# x16 pcie interface @ X0Y1

pcie16 = Interface(mode=InterfaceMode.MASTER, name="pci_express_x16", type="xilinx.com:interface:pcie_7x_mgt_rtl:1.0", of_component="pci_express", preset_proc="pciex16_preset")
part0.interfaces.interface.append(pcie16)
pcie16.preferred_ips = PreferredIps([
    PreferredIp(vendor="xilinx.com", library="ip", name="xdma", order="0"),
    PreferredIp(vendor="xilinx.com", library="ip", name="qdma", order="1"),
    PreferredIp(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", order="2"),    
])

pcie16.port_maps = PortMaps()

pcie16.port_maps.port_map.append(map_xdc_ports("txp", "pcie_tx0_px16", "pcie_lane_txp", "out", pcie_ports_data, pcie_iostd_data))
pcie16.port_maps.port_map.append(map_xdc_ports("txn", "pcie_tx0_nx16", "pcie_lane_txp", "out", pcie_ports_data, pcie_iostd_data, reverse_name_pn))

pcie16.port_maps.port_map.append(map_xdc_ports("rxp", "pcie_rx0_px16", "pcie_lane_rxp", "out", pcie_ports_datarx, pcie_iostd_data))
pcie16.port_maps.port_map.append(map_xdc_ports("rxn", "pcie_rx0_nx16", "pcie_lane_rxp", "out", pcie_ports_datarx, pcie_iostd_data, reverse_name_pn))

pcie16.parameters = Parameters([Parameter(name="block_location", value="X0Y1")])

# reset

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

# TODO: qfp interface


# Components and connections
## SDRAM
for i in range(0, 4):
    component_ddr = Component(
        name=f"ddr4_sdram_c{i}", 
        display_name=f"DDR4 SDRAM C{i}", 
        type=ComponentType.CHIP, sub_type="ddr", 
        major_group="External Memory", 
        part_name="MT40A512M16HA-083E",
        vendor="Micron", spec_url="https://media-www.micron.com/-/media/client/global/documents/products/data-sheet/dram/ddr4/8gb_ddr4_sdram.pdf?rev=74679247a1e24e57b6726071152f1384")
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
    ComponentMode(name="pci_express_x16", display_name="pci_express x16", description="Default mode",
                    interfaces = Interfaces([
                            Interface(name="pci_express_x16"),
                            Interface(name="pcie_perstn", optional=InterfaceOptional.TRUE),
                            Interface(name="pcie_refclk", optional=InterfaceOptional.TRUE),
                    ]),
                    preferred_ips = PreferredIps([
                        PreferredIp(vendor="xilinx.com", library="ip", name="xdma", order="0"),
                        PreferredIp(vendor="xilinx.com", library="ip", name="qdma", order="1"),
                        PreferredIp(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", order="2"),
                    ])),
])

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
    )]
)

# ip associated rule
ip_associated_rules = IpAssociatedRules()
vu13p.ip_associated_rules = ip_associated_rules
ip_associated_rule = IpAssociatedRule(name="default")
ip_associated_rules.ip_associated_rule = ip_associated_rule

ip_associated_rule.ip.append(
    B.Ip(vendor="xilinx.com", library="ip", name="ddr4", version="*", ip_interface="C0_SYS_CLK",
         associated_board_interfaces = [AssociatedBoardInterfaces([
            AssociatedBoardInterface(name=f"ddr4_sdram_c{i}_sys_clk", order=f"{i}"),
         ]) for i in range(0, 4)]
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
            AssociatedBoardInterface(name=ifname, order=str(idx)),
        ])]
    )
for idx, ifname in enumerate(ifclks)])

# system configuration

IpPresets = IpPresets(schema="1.0")
IpPresets.ip_preset = [
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
    IpPreset(preset_proc_name="pciex16_preset", ip = [
        Ip(vendor="xilinx.com", library="ip", name="xdma", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value="X16"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
        ])),
        Ip(vendor="xilinx.com", library="ip", name="qdma", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_speed", value="8.0_GT/s"),
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value="X16"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
        ])),
        Ip(vendor="xilinx.com", library="ip", name="pcie4_uscale_plus", user_parameters = UserParameters([
            UserParameter(name="CONFIG.pl_link_cap_max_link_width", value="X16"),
            UserParameter(name="CONFIG.mode_selection", value="Advanced"),
            UserParameter(name="CONFIG.en_gt_selection", value="true"),
            UserParameter(name="CONFIG.select_quad", value="GTY_Quad_227")
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
]

# pciex16_preset
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
    f.write(serializer.render(IpPresets))

# copy board image file to result
import shutil
shutil.copyfile("img/IMG_0001.jpg", "result/Acompany/vu13p/1.0/vu13p.jpeg")

# generate xitem file
from xml.dom import minidom
xmldoc = minidom.parse("result/Acompany/vu13p/1.0/board.xml")
from generate_xitem_json import createXitemJson
createXitemJson(xmldoc, "result/Acompany/vu13p/1.0/xitem.json")