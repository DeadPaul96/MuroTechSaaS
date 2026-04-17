import os
from flask import Flask, request, jsonify
import pyodbc
from flask_cors import CORS 

app = Flask(__name__)
CORS(app) 

# --- CONFIGURACIÓN DE CONEXIÓN A SQL SERVER ---
# En producción (Render), estas variables deben configurarse en el panel de control
SERVER = os.environ.get('DB_SERVER', r'(localdb)\MSSQLLocalDB')
DATABASE = os.environ.get('DB_NAME', 'FacturacionElectonica')
USERNAME = os.environ.get('DB_USER', 'sa')
PASSWORD = os.environ.get('DB_PASSWORD', 'admin25')
DRIVER = os.environ.get('DB_DRIVER', '{ODBC Driver 17 for SQL Server}')

CONNECTION_STRING = (
    f'DRIVER={DRIVER};'
    f'SERVER={SERVER};'
    f'DATABASE={DATABASE};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    f'TrustServerCertificate=yes;' 
)

def get_db_connection():
    """Establece y retorna la conexión a la base de datos."""
    try:
        conn = pyodbc.connect(CONNECTION_STRING, timeout=5)
        return conn
    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Error de conexión a la BD: {sqlstate}")
        if '08001' in sqlstate:
             print("\n=======================================================")
             print("🛑 ERROR DE CONEXIÓN CRÍTICO: Servidor SQL no encontrado.")
             print("   Asegúrese de que el servicio SQL Server (LocalDB) esté")
             print("   en estado 'En ejecución' en services.msc.")
             print("=======================================================\n")
        return None


UBICACION_DATA = {}
TIPOS_IDENTIFICACION_DATA = []

def cargar_tipos_identificacion_desde_db():
    """Carga los tipos de identificación desde la tabla TiposIdentificacion."""
    global TIPOS_IDENTIFICACION_DATA
    
    conn = get_db_connection()
    if conn is None:
        print("Error: No se pudo conectar a la BD para cargar tipos de identificación.")
        return

    try:
        cursor = conn.cursor()
        sql_query = """
        SELECT CodigoID, DescripcionID, Alcance 
        FROM TiposIdentificacion
        ORDER BY CodigoID
        """
        cursor.execute(sql_query)
        
        temp_data = []
        for row in cursor:
            temp_data.append({
                'codigo': row[0].strip(),
                'descripcion': row[1].strip(),
                'alcance': row[2].strip() if row[2] else ''
            })
        
        TIPOS_IDENTIFICACION_DATA = temp_data
        conn.close()
        
        if TIPOS_IDENTIFICACION_DATA:
            print(f"✅ {len(TIPOS_IDENTIFICACION_DATA)} tipos de identificación cargados exitosamente desde la BD.")
        else:
            print("⚠️ Advertencia: La tabla 'TiposIdentificacion' se cargó, pero no contiene datos.")
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"❌ Error al cargar tipos de identificación desde la BD: {e}")


def cargar_datos_ubicacion_desde_db():
    """Carga y estructura los datos de ubicación desde la tabla CatalogoGeografico."""
    global UBICACION_DATA
    
    conn = get_db_connection()
    if conn is None:
        print("Error: No se pudo conectar a la BD para cargar el catálogo geográfico.")
        return

    try:
        cursor = conn.cursor()
        sql_query = """
        SELECT Nombre_Provincia, Nombre_Canton, Nombre_Distrito, Nombre_Pueblo 
        FROM CatalogoGeografico
        ORDER BY ID_Provincia, ID_Canton, ID_Distrito, ID_Pueblo 
        """
        cursor.execute(sql_query)
        
        temp_data = {}
        for row in cursor:
            provincia, canton, distrito, pueblo = row[0].strip(), row[1].strip(), row[2].strip(), row[3].strip()

            if provincia not in temp_data:
                temp_data[provincia] = {}
            
            if canton not in temp_data[provincia]:
                temp_data[provincia][canton] = {}
            
            if distrito not in temp_data[provincia][canton]:
                temp_data[provincia][canton][distrito] = []
            
            if pueblo not in temp_data[provincia][canton][distrito]: 
                temp_data[provincia][canton][distrito].append(pueblo)
        
        UBICACION_DATA = temp_data
        conn.close()
        
        if UBICACION_DATA:
            print("✅ Datos de ubicación cargados exitosamente desde la BD.")
        else:
             print("⚠️ Advertencia: La tabla 'CatalogoGeografico' se cargó, pero no contiene datos.")
        
    except Exception as e:
        if conn:
            conn.close()
        print(f"❌ Error al cargar datos de ubicación desde la BD: {e}")


cargar_tipos_identificacion_desde_db()
cargar_datos_ubicacion_desde_db()


@app.route('/api/tipos-identificacion', methods=['GET'])
def obtener_tipos_identificacion():
    """Retorna los tipos de identificación disponibles."""
    return jsonify(TIPOS_IDENTIFICACION_DATA)


@app.route('/api/ubicacion', methods=['GET'])
def obtener_ubicacion():
    """Retorna los datos de ubicación jerárquica."""
    return jsonify(UBICACION_DATA)


@app.route('/api/contribuyentes', methods=['POST'])
def registrar_contribuyente():
    data = request.get_json()
    
    nombre_empresa = data.get('empresa')
    razon_social = data.get('razonSocial')
    tipo_cedula = data.get('tipoCedula')
    numero_cedula = data.get('cedula')
    correo_electronico = data.get('email')
    provincia = data.get('provincia')
    canton = data.get('canton')
    distrito = data.get('distrito')
    pueblo = data.get('pueblo')
    detalle_direccion = data.get('direccion')
    ultimo_numero_facturacion = data.get('lastInvoice')
    proveedor_tecnologico = data.get('proveedorTecnologico')
    nombre_archivo_p12 = data.get('nombreArchivoP12', None)
    nombre_contacto = data.get('nombre')
    primer_apellido = data.get('primerApellido')
    segundo_apellido = data.get('segundoApellido', None)
    correo_contacto = data.get('correo')
    telefono = data.get('telefono')
    password = data.get('password')

    if not all([nombre_empresa, razon_social, tipo_cedula, numero_cedula, correo_electronico, 
                provincia, canton, distrito, pueblo, detalle_direccion, 
                ultimo_numero_facturacion, proveedor_tecnologico, 
                nombre_contacto, primer_apellido, correo_contacto, telefono, password]):
        return jsonify({"message": "Faltan campos requeridos."}), 400

    try:
        ultimo_numero_facturacion = int(ultimo_numero_facturacion)
    except (ValueError, TypeError):
        return jsonify({"message": "El último número de facturación debe ser un número válido."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"message": "Error al conectar con la base de datos."}), 500

    cursor = conn.cursor()
    
    sql_insert = """
    INSERT INTO Contribuyentes (
        NombreEmpresa, RazonSocial, TipoCedula, NumeroCedula, 
        Provincia, Canton, Distrito, Pueblo, DetalleDireccion,
        CorreoElectronico, NombreContacto, PrimerApellido, SegundoApellido, 
        CorreoContacto, Telefono,
        UltimoNumeroFacturacion, ProveedorTecnologico,
        Password, NombreArchivoP12
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    try:
        cursor.execute(sql_insert, 
                       nombre_empresa, razon_social, tipo_cedula, numero_cedula,
                       provincia, canton, distrito, pueblo, detalle_direccion,
                       correo_electronico, nombre_contacto, primer_apellido, segundo_apellido,
                       correo_contacto, telefono,
                       ultimo_numero_facturacion, proveedor_tecnologico,
                       password, nombre_archivo_p12)
        
        conn.commit()
        
        cursor.execute("SELECT @@IDENTITY")
        nuevo_id = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            "message": "Contribuyente registrado exitosamente.",
            "id": nuevo_id
        }), 201

    except pyodbc.IntegrityError as e:
        conn.close()
        error_msg = str(e)
        
        if 'NumeroCedula' in error_msg or 'UNIQUE' in error_msg:
            return jsonify({"message": "Error: El número de cédula ya está registrado."}), 409
        elif 'CorreoElectronico' in error_msg:
            return jsonify({"message": "Error: El correo electrónico ya está registrado."}), 409
        elif 'FOREIGN KEY' in error_msg or 'TipoCedula' in error_msg:
            return jsonify({"message": "Error: El tipo de cédula seleccionado no es válido."}), 400
        else:
            return jsonify({"message": "Error: Datos duplicados o inválidos."}), 409
        
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"❌ Error al ejecutar INSERT: {e}")
        return jsonify({
            "message": "Error interno del servidor al procesar la BD.", 
            "detail": str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
