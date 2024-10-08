async function checkToken() {
    const token = document.getElementById("edulutionsetuptoken").value;

    const response = await fetch("/check-token", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: token }),
    });

    const result = await response.json();

    const button = document.getElementById("btn_install");
    const textarea = document.getElementById("edulutionsetuptoken");
    if (result == true) {
        button.disabled = false;
        textarea.style.boxShadow = "0 0 0 2px #74C000";
    } else {
        button.disabled = true;
    }
}

var check_api_status = false;
var check_webdav_status = false;
var check_ldap_status = false;
var check_ldap_access_status = false;

function checkChecks() {
    if (check_api_status && check_webdav_status && check_ldap_status && check_ldap_access_status) {
        document.getElementById("finish_button").disabled = false;
    }
}

async function checkAPIStatus() {
    document.getElementById("api_status").innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";
    document.getElementById("api_status_retry").style.display = "none";

    const response = await fetch("/check-api-status", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    const result = await response.json();
    const icon = document.getElementById("api_status");
    const button = document.getElementById("api_status_retry");
    if (result == true) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;'></i>";
        button.style.display = "block";
    }

    check_api_status = true;
    checkChecks();
}

async function checkWebDAVStatus() {
    document.getElementById("webdav_status").innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";
    document.getElementById("webdav_status_retry").style.display = "none";
    
    const response = await fetch("/check-webdav-status", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    const result = await response.json();
    const icon = document.getElementById("webdav_status");
    const button = document.getElementById("webdav_status_retry");
    if (result == true) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;'></i>";
        button.style.display = "block";
    }

    check_webdav_status = true;
    checkChecks();
}

async function checkLDAPStatus() {
    document.getElementById("ldap_status").innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";
    document.getElementById("ldap_status_retry").style.display = "none";
    
    const response = await fetch("/check-ldap-status", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    const result = await response.json();
    const icon = document.getElementById("ldap_status");
    const button = document.getElementById("ldap_status_retry");
    console.log(result);
    if (result == true) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;'></i>";
        button.style.display = "block";
    }

    check_ldap_status = true;
    checkChecks();
}

async function checkLDAPAccessStatus() {
    document.getElementById("ldap-access_status").innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";
    document.getElementById("ldap-access_status_retry").style.display = "none";
    
    const response = await fetch("/check-ldap-access-status", {
        method: "GET",
        headers: {
            "Content-Type": "application/json",
        }
    });

    const result = await response.json();
    const icon = document.getElementById("ldap-access_status");
    const button = document.getElementById("ldap-access_status_retry");
    console.log(result);
    if (result == true) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;'></i>";
        button.style.display = "block";
    }

    check_ldap_access_status = true;
    checkChecks();
}
    
function checkAll() {
    checkAPIStatus();
    checkWebDAVStatus();
    checkLDAPStatus();
    checkLDAPAccessStatus();
}

function waitforUI() {
    setTimeout(() => {
        setInterval(async () => {
            const response = await fetch("https://" + window.location.hostname)
            if (response.ok) {
                window.location.href = "https://" + window.location.hostname;
            }
        }, 3000)
    }, 30000)
}

function checkInput() {
    const lmn_external_domain = document.getElementById("lmn_external_domain");
    const lmn_binduser_dn = document.getElementById("lmn_binduser_dn");
    const lmn_binduser_pw = document.getElementById("lmn_binduser_pw");
    const lmn_ldap_schema = document.getElementById("lmn_ldap_schema");
    const lmn_ldap_port = document.getElementById("lmn_ldap_port");
    const edulutionui_external_domain = document.getElementById("edulutionui_external_domain");

    const btn_install = document.getElementById("btn_install");

    if (lmn_external_domain.value != "") {
        lmn_external_domain.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        lmn_external_domain.style.boxShadow = "none";
        btn_install.disabled = true;
    }

    if (lmn_binduser_dn.value != "") {
        lmn_binduser_dn.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        lmn_binduser_dn.style.boxShadow = "none";
        btn_install.disabled = true;
    }

    if (lmn_binduser_pw.value != "") {
        lmn_binduser_pw.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        lmn_binduser_pw.style.boxShadow = "none";
        btn_install.disabled = true;
    }

    if (lmn_ldap_schema.value    != "") {
        lmn_ldap_schema.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        lmn_ldap_schema.style.boxShadow = "none";
        btn_install.disabled = true;
    }

    if (lmn_ldap_port.value != "") {
        lmn_ldap_port.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        lmn_ldap_port.style.boxShadow = "none";
        btn_install.disabled = true;
    }

    if (edulutionui_external_domain.value != "") {
        edulutionui_external_domain.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;
    }
    else {
        edulutionui_external_domain.style.boxShadow = "none";
        btn_install.disabled = true;
    }
}