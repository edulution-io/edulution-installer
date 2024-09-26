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
        document.getElementById("finish_button").style.display = "block";
    }
}

async function checkAPIStatus() {
    document.getElementById("api_status").innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";
    document.getElementById("api_status_retry").style.display = "none";

    const external_domain = document.getElementById("api_status").getAttribute("edulution-external-domain");
    
    const response = await fetch("/check-api-status", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ external_domain: external_domain }),
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

    const external_domain = document.getElementById("webdav_status").getAttribute("edulution-external-domain");
    
    const response = await fetch("/check-webdav-status", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ external_domain: external_domain }),
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

    const external_domain = document.getElementById("ldap_status").getAttribute("edulution-external-domain");
    
    const response = await fetch("/check-ldap-status", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ external_domain: external_domain }),
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

    const external_domain = document.getElementById("ldap-access_status").getAttribute("edulution-external-domain");
    const binduser_dn = document.getElementById("ldap-access_status").getAttribute("edulution-binduser-dn");
    const binduser_pw = document.getElementById("ldap-access_status").getAttribute("edulution-binduser-pw");
    
    const response = await fetch("/check-ldap-access-status", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ external_domain: external_domain, binduser_dn: binduser_dn, binduser_pw: binduser_pw }),
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
        window.location.href = "https://" + window.location.hostname
    }, 20000)
}