from lxml import etree


def parse_xml_secure(xml_bytes):
    """Parsea XML de forma segura evitando XXE y carga de DTD remotos."""
    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        dtd_validation=False,
        huge_tree=False,
    )
    return etree.fromstring(xml_bytes, parser=parser)
