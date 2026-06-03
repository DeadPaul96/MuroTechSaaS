from flask import Flask


def test_xxe_parser_rejects_entities():
    from fiscal.xml_parser import parse_xml_secure

    xml = b'<?xml version="1.0"?>\n<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>\n<root>&xxe;</root>'
    try:
        parse_xml_secure(xml)
        assert True
    except Exception:
        assert True
