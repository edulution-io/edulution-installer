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
        document.getElementById("cert_button").disabled = false;
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
    if (result.status) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
        check_api_status = true;
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
        button.style.display = "block";
        check_api_status = false;
    }

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
    if (result.status) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
        check_webdav_status = true;
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
        button.style.display = "block";
        check_webdav_status = false;
    }

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
    if (result.status) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
        check_ldap_status = true;
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
        button.style.display = "block";
        check_ldap_status = false;
    }

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
    if (result.status) {
        icon.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        button.style.display = "none";
        check_ldap_access_status = true;
    } else {
        icon.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
        button.style.display = "block";
        check_ldap_access_status = false;
    }

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

    if (lmn_ldap_schema.value != "") {
        lmn_ldap_schema.style.boxShadow = "0 0 0 2px #74C000";
        btn_install.disabled = false;

        if (lmn_ldap_schema.value == "ldap" && lmn_ldap_port.value == 636) {
            lmn_ldap_port.value = 389;
        }
        if (lmn_ldap_schema.value == "ldaps" && lmn_ldap_port.value == 389) {
            lmn_ldap_port.value = 636;
        }
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

function loadDomain() {
    document.getElementById('edulutionui_external_domain').value = window.location.hostname;
}

function loadCertificateContent(certificate_type) {
    document.getElementById("content_1").style.display = "none";
    document.getElementById("content_2").style.display = "none";
    document.getElementById("content_3").style.display = "none";
    
    document.getElementById("content_" + certificate_type.value).style.display = "block";
}

function checkCertificateInput() {
    const cert_domain = document.getElementById("cert_domain");
    const cert_country_code = document.getElementById("cert_country_code");
    const cert_state = document.getElementById("cert_state");
    const cert_city = document.getElementById("cert_city");
    const cert_organisation = document.getElementById("cert_organisation");
    const cert_valid_days = document.getElementById("cert_valid_days");

    const cert_generate_btn = document.getElementById("cert_generate_btn");

    let cert_domain_valid = false;
    let cert_country_code_valid = false;
    let cert_state_valid = false;
    let cert_city_valid = false;
    let cert_organisation_valid = false;
    let cert_valid_days_valid = false;

    if (cert_domain.value != "") {
        cert_domain.style.boxShadow = "0 0 0 2px #74C000";
        cert_domain_valid = true;
    }
    else {
        cert_domain.style.boxShadow = "none";
        cert_domain_valid = false;
    }

    if (cert_country_code.value != "") {
        cert_country_code.style.boxShadow = "0 0 0 2px #74C000";
        cert_country_code_valid = true;
    }
    else {
        cert_country_code.style.boxShadow = "none";
        cert_country_code_valid = false;
    }

    if (cert_state.value != "") {
        cert_state.style.boxShadow = "0 0 0 2px #74C000";
        cert_state_valid = true;
    }
    else {
        cert_state.style.boxShadow = "none";
        cert_state_valid = false;
    }

    if (cert_city.value != "") {
        cert_city.style.boxShadow = "0 0 0 2px #74C000";
        cert_city_valid = true;
    }
    else {
        cert_city.style.boxShadow = "none";
        cert_city_valid = false;
    }

    if (cert_organisation.value != "") {
        cert_organisation.style.boxShadow = "0 0 0 2px #74C000";
        cert_organisation_valid = true;
    }
    else {
        cert_organisation.style.boxShadow = "none";
        cert_organisation_valid = false;
    }

    if (cert_valid_days.value != "") {
        cert_valid_days.style.boxShadow = "0 0 0 2px #74C000";
        cert_valid_days_valid = true;
    }
    else {
        cert_valid_days.style.boxShadow = "none";
        cert_valid_days_valid = false;
    }


    if (cert_domain_valid && cert_country_code_valid && cert_state_valid && cert_city_valid && cert_organisation_valid && cert_valid_days_valid) {
        cert_generate_btn.disabled = false;
    }
    else {
        cert_generate_btn.disabled = true;
    }
}

async function generateSSCertificate() {
    const cert_country_code = document.getElementById("cert_country_code").value;
    const cert_state = document.getElementById("cert_state").value;
    const cert_city = document.getElementById("cert_city").value;
    const cert_organisation = document.getElementById("cert_organisation").value;
    const cert_valid_days = document.getElementById("cert_valid_days").value;

    const ss_certificate_status = document.getElementById("ss_certificate_status");
    ss_certificate_status.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";

    const install_button = document.getElementById("install_button");
    install_button.disabled = true;

    const response = await fetch("/create-ss-certificate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            countrycode: cert_country_code,
            state: cert_state,
            city: cert_city,
            organisation: cert_organisation,
            valid_days: cert_valid_days
        }),
    });

    const result = await response.json();

    if (result.status) {
        ss_certificate_status.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        install_button.disabled = false;
    } else {
        ss_certificate_status.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
    }
}

function checkLECertificateInput() {
    const lecert_domain = document.getElementById("lecert_domain");
    const lecert_email = document.getElementById("lecert_email");

    const lecert_create_btn = document.getElementById("lecert_create_btn");

    let lecert_domain_valid = false;
    let lecert_email_valid = false;

    if (lecert_domain.value != "") {
        lecert_domain.style.boxShadow = "0 0 0 2px #74C000";
        lecert_domain_valid = true;
    }
    else {
        lecert_domain.style.boxShadow = "none";
        lecert_domain_valid = false;
    }

    if (lecert_email.value != "") {
        lecert_email.style.boxShadow = "0 0 0 2px #74C000";
        lecert_email_valid = true;
    }
    else {
        lecert_email.style.boxShadow = "none";
        lecert_email_valid = false;
    }

    if (lecert_domain_valid && lecert_email_valid) {
        lecert_create_btn.disabled = false;
    }
    else {
        lecert_create_btn.disabled = true;
    }
}

async function createLECertificate() {
    const lecert_email = document.getElementById("lecert_email").value;

    const le_certificate_status = document.getElementById("le_certificate_status");
    le_certificate_status.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";

    const install_button = document.getElementById("install_button");
    install_button.disabled = true;

    const response = await fetch("/create-le-certificate", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            email: lecert_email
        }),
    });

    const result = await response.json();

    if (result.status) {
        le_certificate_status.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        install_button.disabled = false;
    } else {
        le_certificate_status.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
    }
}

function checkUploadCertificateInput() {
    const certificate_file = document.getElementById("certificate_file");
    const key_file = document.getElementById("key_file");

    const cert_upload_btn = document.getElementById("cert_upload_btn");

    let certificate_file_valid = false;
    let key_file_valid = false;

    if (certificate_file.value != "") {
        certificate_file.style.boxShadow = "0 0 0 2px #74C000";
        certificate_file_valid = true;
    }
    else {
        certificate_file.style.boxShadow = "none";
        certificate_file_valid = false;
    }

    if (key_file.value != "") {
        key_file.style.boxShadow = "0 0 0 2px #74C000";
        key_file_valid = true;
    }
    else {
        key_file.style.boxShadow = "none";
        key_file_valid = false;
    }

    if (certificate_file_valid && key_file_valid) {
        cert_upload_btn.disabled = false;
    }
    else {
        cert_upload_btn.disabled = true;
    }
}

async function uploadCertificate() {
    const certificate_file = document.getElementById("certificate_file").files[0];
    const key_file = document.getElementById("key_file").files[0];

    const upload_certificate_status = document.getElementById("upload_certificate_status");
    upload_certificate_status.innerHTML = "<i class='fa-solid fa-spinner fa-spin'></i>";

    const install_button = document.getElementById("install_button");
    install_button.disabled = true;

    formdata = new FormData();
    formdata.append("cert", certificate_file);
    formdata.append("key", key_file);

    const response = await fetch("/upload-certificate", {
        method: "POST",
        body: formdata
    });

    const result = await response.json();

    if (result.status) {
        upload_certificate_status.innerHTML = "<i class='fa-solid fa-circle-check' style='color: #2ecc71;'></i>";
        install_button.disabled = false;
    } else {
        upload_certificate_status.innerHTML = "<i class='fa-solid fa-circle-xmark' style='color: #e74c3c;' title='" + result.message.normalize() + "'></i>";
    }
}