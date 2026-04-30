import unittest

from web_browsing_activity_recorder.properties import properties
from mo.core.plugin.models.properties import PropertyType


class TestWebBrowsingProperties(unittest.TestCase):

    def test_properties_object_exists(self):
        self.assertIsNotNone(properties)

    def test_server_host_field_exists(self):
        self.assertTrue(properties.has_property("server_host"))

    def test_server_host_text(self):
        self.assertEqual(properties.get_type("server_host"), PropertyType.TEXT)

    def test_server_host_default(self):
        self.assertEqual(properties.get_default_values()["server_host"], "localhost")

    def test_server_port_field_exists(self):
        self.assertTrue(properties.has_property("server_port"))

    def test_server_port_int(self):
        self.assertEqual(properties.get_type("server_port"), PropertyType.INT)

    def test_server_port_default(self):
        self.assertEqual(properties.get_default_values()["server_port"], 3000)

    def test_export_csv_field_exists(self):
        self.assertTrue(properties.has_property("export_to_csv"))

    def test_export_csv_default_false(self):
        self.assertEqual(properties.get_default_values()["export_to_csv"], False)

    def test_stream_clients_field_exists(self):
        self.assertTrue(properties.has_property("stream_to_clients"))

    def test_stream_clients_default_true(self):
        self.assertEqual(properties.get_default_values()["stream_to_clients"], True)

    def test_four_fields_total(self):
        self.assertEqual(len(properties.get_default_values()), 4)


if __name__ == "__main__":
    unittest.main()
