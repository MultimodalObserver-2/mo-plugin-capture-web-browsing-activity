from mo.core import Properties
from mo import translate

properties = Properties()

properties.add_text("server_host", translate("property.server_host"))
properties.set_default("server_host", "localhost")

properties.add_int("server_port", translate("property.server_port"), min=1024, max=65535, step=1, )
properties.set_default("server_port", 3000)
properties.add_bool("export_to_csv", translate("property.export_to_csv"))
properties.set_default("export_to_csv", False)
properties.add_bool("stream_to_clients", translate("property.stream_to_clients"))
properties.set_default("stream_to_clients", True)
