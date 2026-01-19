#!/usr/bin/env python3
"""
Configuración del Token de CoinCap API en el Keychain de macOS.

Uso:
    python3 setup_coincap_token.py

El token se obtiene desde:
    https://docs.coincap.io > Request API Key
"""

import keyring
import getpass

SERVICE_NAME = "DashboardFinanciero"
USERNAME = "coincap_api"


def main():
    print("\n" + "="*60)
    print("🔐 CONFIGURACIÓN DE API KEY DE COINCAP")
    print("="*60)
    
    # Verificar si ya existe un token
    existing_token = keyring.get_password(SERVICE_NAME, USERNAME)
    if existing_token:
        print(f"\n✅ Ya existe un token guardado ({len(existing_token)} caracteres)")
        
        overwrite = input("\n¿Deseas reemplazarlo? (s/N): ").strip().lower()
        if overwrite != 's':
            print("Operación cancelada.")
            return
    
    print("\n📋 Instrucciones para obtener tu API Key:")
    print("   1. Ve a https://docs.coincap.io")
    print("   2. Haz click en 'Request API Key'")
    print("   3. Copia tu API Key")
    print("\n   Nota: El tier gratuito incluye 4,000 créditos/mes")
    
    print("\n" + "-"*60)
    token = getpass.getpass("Introduce tu API Key de CoinCap: ")
    
    if not token or len(token) < 10:
        print("❌ Token inválido. Debe tener al menos 10 caracteres.")
        return
    
    # Guardar en el Keychain
    try:
        keyring.set_password(SERVICE_NAME, USERNAME, token)
        print(f"\n✅ API Key guardada correctamente en el Keychain de macOS")
        print(f"   Longitud: {len(token)} caracteres")
        print("\n🚀 Ahora puedes reiniciar el backend y cargar históricos:")
        print("   curl -X POST http://localhost:8000/api/history/load-all")
    except Exception as e:
        print(f"\n❌ Error al guardar el token: {e}")


if __name__ == "__main__":
    main()
