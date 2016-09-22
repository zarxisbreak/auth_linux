#!/usr/bin/env python
from platform import dist
from sys import exit
from subprocess import call, Popen, PIPE

import pexpect
token_pin = input('Enter PIN: ')

d = {}
d['Fedora'] = 'yum'
d['Redhat'] = 'yum'
d['LinuxMint'] = 'apt-get'
d['Ubuntu'] = 'apt-get'
d['Debian'] = 'apt-get'

package_manager = d.get(dist()[0])
install_packages = call(["sudo", package_manager, "install","-y","libccid", "pcscd", "libpam-p11", "libp11-2", "libengine-pkcs11-openssl", "opensc"])
if install_packages != 0:
	exit("check your internet connection\n")
download_library = call(["wget", "--no-check-certificate", "https://download.rutoken.ru/Rutoken/PKCS11Lib/Current/Linux/x64/rtpkcs11ecp/librtpkcs11ecp.so"]) # 200 ok?
if download_library != 0:
	exit("check your internet connection\n")
call(["sudo", "cp", "librtpkcs11ecp.so", "/usr/lib"])
call(["sudo", "chmod", "644", "/usr/lib/librtpkcs11ecp.so"])
check_token = call(["pkcs11-tool", "--module", "/usr/lib/librtpkcs11ecp.so", "-T"])
if check_token != 0:
	exit("check the token is inserted correctly\n")

proc = Popen(["pkcs11-tool", "--module", "/usr/lib/librtpkcs11ecp.so", "-O"], stdout = PIPE).communicate()
if len(str(proc).split("\\n")) > 1:
	cert_id =  str(proc).split("\\n")[2].split()[1]
	cmd_cert = "pkcs11-tool --module /usr/lib/librtpkcs11ecp.so -r -y cert --id {" + cert_id + "} > cert.crt"
	call(cmd_cert, shell=True)

else:
	call("pkcs11-tool --module /usr/lib/librtpkcs11ecp.so --keypairgen --key-type rsa:2048 -l --id 45", shell=True)
	openssl_cert = pexpect.spawn('openssl')
	openssl_cert.expect('OpenSSL>')
	openssl_cert.sendline('engine dynamic -pre SO_PATH:/usr/lib/engines/engine_pkcs11.so -pre ID:pkcs11 -pre LIST_ADD:1 -pre LOAD -pre MODULE_PATH:/usr/lib/librtpkcs11ecp.so')
	openssl_cert.expect('OpenSSL>')
	print openssl_cert.before
	openssl_cert.sendline('req -engine pkcs11 -new -key 0:45 -keyform engine -x509 -out cert.crt -outform DER')
	openssl_cert.expect('PKCS#11 token PIN:')
	print openssl_cert.before
	openssl_cert.sendline(str(token_pin))
	openssl_cert.expect('OpenSSL>')
	print openssl_cert.before
	openssl_cert.sendline('q')
	call("pkcs11-tool --module /usr/lib/librtpkcs11ecp.so -l -y cert -w cert.crt --id 45", shell=True)
call("openssl x509 -in cert.crt -out cert.pem -inform DER -outform PEM", shell=True)
call("mkdir  -p ~/.eid && chmod 0755 ~/.eid && cat cert.pem >> ~/.eid/authorized_certificates && chmod 0644 ~/.eid/authorized_certificates", shell=True)
call("sudo echo 'Name: Pam_p11\nDefault: yes\nPriority: 800\nAuth-Type: Primary\nAuth: sufficient pam_p11_opensc.so /usr/lib/librtpkcs11ecp.so\n' > /usr/share/pam-configs/p11", shell=True)
call("sudo pam-auth-update", shell=True) #todo: diff
call("sudo login")
