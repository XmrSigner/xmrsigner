SSH_PRIVATE_KEY := $(PWD)/xmrsigner_dev_ssh
SRC_DIR := $(PWD)/src
DEV_DEVICE_IP := ''
DEV_DEVICE_WIFI_IP := '192.168.4.1'

default:
	true

resources:
	@echo 'compress_resources...'
	tools/compress_resources.py xmrsigner.resources src/xmrsigner/resources

clean:
	@echo 'clean py cache files...'
	@find src -name __pycache__ -exec rm -rf \{\} \; >&2 || true

version:
	grep VERSION src/xmrsigner/controller.py | awk -F'"' '{ print $2 }'

checksums: clean
	@echo 'generate sha256 checksums...'
	@find src -type f -exec sha256sum --tag {} \; > SHA256
	@find tools -type f -exec sha256sum --tag {} \; >> SHA256
	@find docs -type f -exec sha256sum --tag {} \; >> SHA256
	@sha256sum --tag requirements.txt >> SHA256
	@sha256sum --tag setup.py >> SHA256
	@sha256sum --tag Makefile >> SHA256
	@sha256sum --tag README.md >> SHA256
	@sha256sum --tag LICENSE.md >> SHA256
	@rm -f SHA256.sig
	@git add SHA256

sign: checksums
	@echo 'Sign the checksums...'
	@tools/sign.sh
	@cat SHA256 >> SHA256.sig
	@git add SHA256.sig

verify:
	@echo 'Verify source files...'
	@signify-openbsd -C -p xmrsigner.pub -x SHA256.sig | grep -v ': OK'
	@echo 'Source is verified!'

.increment-patch:
	@tools/increment_version.py --patch

patch: .increment-patch checksums sign version
	@tools/tag_version.py

.increment-minor:
	@tools/increment_version.py --minor

minor: .increment-minor checksums sign version
	@tools/tag_version.py

.increment-major:
	@tools/increment_version.py --major

major: .increment-major checksums sign version
	@tools/tag_version.py

image-clean-bookworm:
	@echo 'Remove folder devimage for bookworm...'
	@rm -rf devimage

image-clean-buster:
	@echo 'Remove folder devimage for buster...'
	@rm -rf devimage-buster

image-clean: image-clean-buster image-clean-bookworm
	@true

image-bookworm:
	@echo 'Build PiOS (bookworm) image with XmrSigner for Development...'
	@tools/create_image_bookworm.sh

image-buster:
	@echo 'Build PiOS (buster) image with XmrSigner for Development...'
	@tools/create_image_buster.sh

unixtime:
	date +unixtime:%s?tz=%Z | qr

dev-device-ip:
	@echo 'Search IP of dev device via nmap...'
	$(eval DEV_DEVICE_IP := $(shell tools/find_dev_device.sh))
	@if [ -z "$(DEV_DEVICE_IP)" ]; then \
		echo "DEV_DEVICE_IP is empty. Is the pi zero connected and up?"; \
		exit 1; \
	fi

dev-device-show-ip: dev-device-ip
	@echo $(DEV_DEVICE_IP)

dev-device-sync: dev-device-ip clean
	@echo 'Sync via scp...'
	@scp -r -i $(SSH_PRIVATE_KEY) $(SRC_DIR)/xmrsigner xmrsigner@$(DEV_DEVICE_IP):/opt/xmrsigner/

dev-device-rsync: dev-device-ip clean
	@echo 'Sync via rsync...'
	@rsync -az --info=progress2 -e "ssh -i $(SSH_PRIVATE_KEY)" $(SRC_DIR)/xmrsigner xmrsigner@$(DEV_DEVICE_IP):/opt/xmrsigner/

dev-device-shell: dev-device-ip
	ssh -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_IP)

dev-device-log: dev-device-ip
	ssh -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_IP) 'tail -f /var/log/xmrsigner.log'

dev-device-shutdown: dev-device-ip
	@ssh -t -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_IP) 'sudo halt'

dev-device-reboot: dev-device-ip
	@ssh -t -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_IP) 'sudo reboot'

dev-device-wifi-shell:
	ssh -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_WIFI_IP)

dev-device-wifi-shell-reatach:
	ssh -t -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_WIFI_IP) 'screen -r'

dev-device-time-sync: dev-device-ip
	date +'%s %Z' | ssh -t -i $(SSH_PRIVATE_KEY) xmrsigner@$(DEV_DEVICE_IP) 'read -r ts tz; sudo date -s @${ts}; echo $tz | sudo tee /etc/timezone; sudo dpkg-reconfigure -f noninteractive tzdata'
