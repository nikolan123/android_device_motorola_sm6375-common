#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
#
# SPDX-FileCopyrightText: The LineageOS Project
# SPDX-License-Identifier: Apache-2.0
#

import json
from pathlib import Path

from extract_utils.fixups_blob import (
    blob_fixup,
    blob_fixups_user_type,
)
from extract_utils.fixups_lib import (
    lib_fixups,
    lib_fixups_user_type,
)
from extract_utils.main import (
    ExtractUtils,
    ExtractUtilsModule,
)

namespace_imports = [
    'device/motorola/sm6375-common',
    'hardware/motorola',
    'hardware/qcom-caf/sm8350',
    'hardware/qcom-caf/wlan',
    'vendor/qcom/opensource/commonsys/display',
    'vendor/qcom/opensource/commonsys-intf/display',
    'vendor/qcom/opensource/dataservices',
    'vendor/qcom/opensource/display',
]

def lib_fixup_vendor_suffix(lib: str, partition: str, *args, **kwargs):
    return f'{lib}_{partition}' if partition == 'vendor' else None


def fixup_sf_task_profiles(_ctx, _file, file_path: str, *_args, **_kwargs):
    # Override the standard framework profiles through vendor configuration.
    # SFMainPolicy runs during init, so later helpers inherit its CPU placement.
    path = Path(file_path)
    config = json.loads(path.read_text())
    names = ('SFMainPolicy', 'SFRenderEnginePolicy')
    # Remove the obsolete custom late-hook profile when re-extracting local blobs.
    replaced_names = (*names, 'SFMainRenderPolicy')
    config['Profiles'] = [p for p in config['Profiles'] if p['Name'] not in replaced_names]
    for name in names:
        config['Profiles'].append({
            'Name': name,
            'Actions': [{
                'Name': 'JoinCgroup',
                'Params': {'Controller': 'cpuset', 'Path': 'surfaceflinger'},
            }],
        })
    path.write_text(json.dumps(config, indent=2) + '\n')


lib_fixups: lib_fixups_user_type = {
    **lib_fixups,
    (
        'com.qualcomm.qti.dpm.api@1.0',
        'libmmosal',
        'vendor.qti.diaghal@1.0',
        'vendor.qti.hardware.fm@1.0',
        'vendor.qti.hardware.wifidisplaysession@1.0',
        'vendor.qti.imsrtpservice@3.0',
    ): lib_fixup_vendor_suffix,
}

blob_fixups: blob_fixups_user_type = {
    'vendor/etc/task_profiles.json': blob_fixup()
        .call(fixup_sf_task_profiles, need_tmp_dir=False),
    'system_ext/etc/permissions/moto-telephony.xml': blob_fixup()
        .regex_replace('/system/', '/system_ext/'),
    'system_ext/lib64/libwfdnative.so': blob_fixup()
        .add_needed('libinput_shim.so'),
    #'system_ext/priv-app/ims/ims.apk': blob_fixup()
    #    .apktool_patch('ims-patches'),
    (
        'vendor/lib64/libdpps.so',
        'vendor/lib64/libsnapdragoncolor-manager.so',
    ): blob_fixup()
        .replace_needed('libtinyxml2.so', 'libtinyxml2-v34.so'),
    'vendor/lib64/libwvhidl.so': blob_fixup()
        .add_needed('libcrypto_shim.so'),
    ('vendor/bin/init.kernel.post_boot-blair.sh', 'vendor/bin/init.kernel.post_boot-holi.sh'): blob_fixup()
        .regex_replace('ro.boot.using_zram_from_fstab', 'ro.vendor.zram.swapon'),
}  # fmt: skip

module = ExtractUtilsModule(
    'sm6375-common',
    'motorola',
    blob_fixups=blob_fixups,
    lib_fixups=lib_fixups,
    namespace_imports=namespace_imports,
)

module.add_proprietary_file('proprietary-files-fm.txt').add_copy_files_guard(
    'TARGET_HAS_FM', 'true'
)

if __name__ == '__main__':
    utils = ExtractUtils.device(module)
    utils.run()
