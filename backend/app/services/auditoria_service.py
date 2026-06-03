"""Registro de auditoría para cambios en entidades críticas."""
import uuid
from datetime import datetime

from flask import request

from app.extensions import db
from app.models import AuditoriaLog


class AuditoriaService:
    SENSITIVE_FIELDS = {'api_password', 'api_pin_p12', 'password', 'api_pass', 'api_pin'}

    @staticmethod
    def _sanitize(data: dict | None) -> dict | None:
        if not data:
            return data
        out = {}
        for k, v in data.items():
            if k in AuditoriaService.SENSITIVE_FIELDS:
                out[k] = '***'
            else:
                out[k] = v
        return out

    @staticmethod
    def log_change(
        *,
        usuario_id: str | None,
        entidad: str,
        accion: str,
        valores_antes=None,
        valores_despues=None,
        entidad_id: str | None = None,
    ) -> AuditoriaLog | None:
        try:
            entry = AuditoriaLog(
                id=str(uuid.uuid4()),
                usuario_id=usuario_id,
                entidad=entidad,
                accion=accion,
                valores_antes=AuditoriaService._sanitize(valores_antes),
                valores_despues=AuditoriaService._sanitize(valores_despues),
                timestamp=datetime.utcnow(),
                ip_address=request.remote_addr if request else None,
                user_agent=(request.headers.get('User-Agent', '')[:500] if request else None),
            )
            if entidad_id and isinstance(entry.valores_despues, dict):
                entry.valores_despues = {**entry.valores_despues, '_id': entidad_id}
            db.session.add(entry)
            db.session.commit()
            return entry
        except Exception:
            db.session.rollback()
            return None

    @staticmethod
    def snapshot_empresa(empresa) -> dict:
        if not empresa:
            return {}
        return {
            'id': empresa.id,
            'razon_social': empresa.razon_social,
            'nombre_comercial': empresa.nombre_comercial,
            'email_contacto': empresa.email_contacto,
            'api_usuario': empresa.api_usuario,
            'ambiente_hacienda': getattr(empresa, 'ambiente_hacienda', None),
            'plan_tipo': empresa.plan_tipo,
            'plan_estado': empresa.plan_estado,
        }
