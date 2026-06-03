"""Cliente MH — mapeo de estados y consulta (mock)."""
from unittest.mock import MagicMock, patch

from fiscal.hacienda_client import HaciendaClient, mapear_estado_mh


def test_mapear_estado_aceptado():
    assert mapear_estado_mh({'ind-estado': 'aceptado'}) == 'Aceptada MH'


def test_mapear_estado_rechazado():
    assert mapear_estado_mh({'estado': 'rechazado'}) == 'Rechazada MH'


@patch('fiscal.hacienda_client.requests.get')
@patch.object(HaciendaClient, 'obtener_token', return_value='tok-test')
def test_consultar_estado_recepcion(mock_token, mock_get):
    mock_get.return_value = MagicMock(ok=True, status_code=200, json=lambda: {'ind-estado': 'procesando'})
    client = HaciendaClient(ambiente='stag')
    out = client.consultar_estado_recepcion('506' + '1' * 47, 'user', 'pass')
    assert out['body']['ind-estado'] == 'procesando'
    mock_get.assert_called_once()
    assert '506' in mock_get.call_args[0][0]
