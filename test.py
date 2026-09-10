from snowflake.connector import connect

print("=" * 60)
print("TEST DE CONEXIÓN A SNOWFLAKE CON JWT")
print("=" * 60)

try:
    print("\n🔄 Intentando conectar a Snowflake...")
    print(f"   Cuenta: mu75918")
    print(f"   Usuario: SVC_DBT_PIPELINE_DEPLOY")
    print(f"   Rol: DBT_PIPELINE_DEVELOPER")
    
    connection = connect(
        account="mu75918",
        user="SVC_DBT_PIPELINE_DEPLOY",
        private_key_path="./terraform/key/svc_dbt_pipeline_deploy_key.p8",
        role="DBT_PIPELINE_DEVELOPER"
    )
    
    print("\n✅ ¡CONEXIÓN EXITOSA!")
    print(f"   Usuario conectado: {connection.user}")
    print(f"   Rol: {connection.role}")
    
    # Query de prueba
    cursor = connection.cursor()
    cursor.execute("SELECT CURRENT_USER() as user, CURRENT_ROLE() as role;")
    result = cursor.fetchone()
    print(f"\n✅ Query ejecutado correctamente:")
    print(f"   Usuario: {result[0]}")
    print(f"   Rol: {result[1]}")
    
    connection.close()
    print("\n" + "=" * 60)
    print("🎉 TODO FUNCIONA - Estás listo para Terraform")
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ ERROR DE CONEXIÓN")
    print(f"   Tipo de error: {type(e).__name__}")
    print(f"   Mensaje: {e}")
    print("\n" + "=" * 60)
