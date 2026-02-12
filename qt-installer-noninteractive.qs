/* Qt Installer Framework scripting: auto-accept license and set target dir */
function Controller() {
    installer.autoAcceptLicense();
    // Default install path
    var targetDir = installer.value("TargetDir");
    if (!targetDir || targetDir.length == 0) {
        installer.setValue("TargetDir", "/opt/qt/5.15.2");
    }
    installer.setValue("LicenseAccepted", "true");
}

function Component() {}
