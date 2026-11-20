
const rls_mcan = scripting.addModule("/drivers/mcan/mcan", {}, false);
const rls_mcan1 = rls_mcan.addInstance();
rls_mcan1.$name = "CONFIG_MCAN0";
rls_mcan1.MCAN.$assign = "MCANA";
rls_mcan1.MCAN.RX.$assign = "PAD_BO";
rls_mcan1.MCAN.TX.$assign = "PAD_BN";
