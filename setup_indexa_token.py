#!/usr/bin/env python3
"""
Configuración del Token de Indexa Capital en el Keychain de macOS.

Uso:
    python3 setup_indexa_token.py

El token se obtiene desde:
    https://indexacapital.com > Mi cuenta > Configuración > Aplicaciones > API Token
"""

import keyring
import getpass

SERVICE_NAME = "DashboardFinanciero"
USERNAME = "indexa_api"


def main():
    print("\n" + "="*60)
    print("🔐 CONFIGURACIÓN DE TOKEN DE INDEXA CAPITAL")
    print("="*60)
    
    # Verificar si ya existe un token
    existing_token = keyring.get_password(SERVICE_NAME, USERNAME)
    if existing_token:
        print(f"\n✅ Ya existe un token guardado ({len(existing_token)} caracteres)")
        print("   Puedes verificarlo ejecutando: python3 indexa_proxy.py")
        
        overwrite = input("\n¿Deseas reemplazarlo? (s/N): ").strip().lower()
        if overwrite != 's':
            print("Operación cancelada.")
            return
    
    print("\n📋 Instrucciones para obtener tu token:")
    print("   1. Ve a https://indexacapital.com")
    print("   2. Inicia sesión en tu cuenta")
    print("   3. Ve a: Configuración > Aplicaciones")
    print("   4. Copia tu API Token")
    
    print("\n" + "-"*60)
    token = getpass.getpass("Introduce tu API Token de Indexa: ")
    
    if not token or len(token) < 10:
        print("❌ Token inválido. Debe tener al menos 10 caracteres.")
        return
    
    # Guardar en el Keychain
    try:
        keyring.set_password(SERVICE_NAME, USERNAME, token)
        print(f"\n✅ Token guardado correctamente en el Keychain de macOS")
        print(f"   Longitud: {len(token)} caracteres")
        print("\n🚀 Ahora puedes ejecutar el proxy:")
        print("   python3 indexa_proxy.py")
    except Exception as e:
        print(f"\n❌ Error al guardar el token: {e}")


if __name__ == "__main__":
    main()
