DOC_FACTURA, DOC_NOTA_DEBITO, DOC_NOTA_CREDITO, DOC_TIQUETE = '01', '02', '03', '04'
DOC_FACTURA_EXPORTACION = '05'
DOC_FACTURA_COMPRA = '08'
DOC_CONT_FACTURA, DOC_CONT_TIQUETE = '09', '10'
DOC_ROOT = {
    '01': 'FacturaElectronica', '02': 'NotaDebitoElectronica', '03': 'NotaCreditoElectronica',
    '04': 'TiqueteElectronico',
    '05': 'FacturaElectronicaExportacion',
    '08': 'FacturaElectronicaCompra',
    '09': 'FacturaElectronica', '10': 'TiqueteElectronico',
}
DOC_XMLNS = {
    '01': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica',
    '02': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaDebitoElectronica',
    '03': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/notaCreditoElectronica',
    '04': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/tiqueteElectronico',
    '05': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaExportacion',
    '08': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronicaCompra',
    '09': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/facturaElectronica',
    '10': 'https://cdn.comprobanteselectronicos.go.cr/xml-schemas/v4.4/tiqueteElectronico',
}
XSI_NS = 'http://www.w3.org/2001/XMLSchema-instance'
PROVEEDOR_SISTEMAS = 'MUROTECH'
TARIFA_IVA = {0: '01', 1: '02', 2: '03', 4: '04', 13: '08'}
# Situación del comprobante: 1=normal, 2=contingencia, 3=sin internet
SITUACION_NORMAL = '1'
SITUACION_CONTINGENCIA = '2'
SITUACION_SIN_INTERNET = '3'
