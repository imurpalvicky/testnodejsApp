import groovy.json.JsonSlurper
import groovy.json.JsonBuilder
import java.net.URLEncoder

// Configuration - Set these variables
def CLIENT_ID = env.CLIENT_ID ?: 'your-client-id'
def CLIENT_SECRET = env.CLIENT_SECRET ?: 'your-client-secret'
def TENANT_ID = env.TENANT_ID ?: 'your-tenant-id'
def SITE_URL = 'https://yourcompany.sharepoint.com/sites/yoursite'
def SEARCH_STRING = 'Documents'  // Library name to search for
def ARTIFACT_PATH = "${WORKSPACE}/build/artifact.zip"  // File to upload

// Main execution
try {
    echo "Starting SharePoint upload process..."
    
    // Step 1: Get access token
    echo "Getting access token..."
    def accessToken = getAccessToken(CLIENT_ID, CLIENT_SECRET, TENANT_ID)
    echo "Access token obtained successfully"
    
    // Step 2: Find document library
    echo "Searching for document library containing: ${SEARCH_STRING}"
    def libraryId = findDocumentLibrary(accessToken, SITE_URL, SEARCH_STRING)
    
    if (!libraryId) {
        error("No document library found with name containing: ${SEARCH_STRING}")
    }
    
    echo "Found document library ID: ${libraryId}"
    
    // Step 3: Upload file
    echo "Uploading file: ${ARTIFACT_PATH}"
    def fileId = uploadFile(accessToken, SITE_URL, libraryId, ARTIFACT_PATH)
    
    echo "SUCCESS: File uploaded to SharePoint with ID: ${fileId}"
    
} catch (Exception e) {
    error("SharePoint upload failed: ${e.message}")
}

// Function to get SharePoint access token
def getAccessToken(clientId, clientSecret, tenantId) {
    def tokenUrl = "https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token"
    
    def postBody = "grant_type=client_credentials&client_id=${URLEncoder.encode(clientId, 'UTF-8')}&client_secret=${URLEncoder.encode(clientSecret, 'UTF-8')}&scope=https://graph.microsoft.com/.default"
    
    def response = httpRequest(
        httpMode: 'POST',
        url: tokenUrl,
        contentType: 'APPLICATION_FORM',
        requestBody: postBody,
        validResponseCodes: '200'
    )
    
    def jsonSlurper = new JsonSlurper()
    def result = jsonSlurper.parseText(response.content)
    
    return result.access_token
}

// Function to find document library by search string
def findDocumentLibrary(accessToken, siteUrl, searchString) {
    def siteUri = new URI(siteUrl)
    def hostname = siteUri.getHost()
    def sitePath = siteUri.getPath()
    
    def apiUrl = "https://graph.microsoft.com/v1.0/sites/${hostname}:${sitePath}:/lists"
    
    def response = httpRequest(
        httpMode: 'GET',
        url: apiUrl,
        customHeaders: [
            [name: 'Authorization', value: "Bearer ${accessToken}"],
            [name: 'Accept', value: 'application/json']
        ],
        validResponseCodes: '200'
    )
    
    def jsonSlurper = new JsonSlurper()
    def data = jsonSlurper.parseText(response.content)
    
    // Search through document libraries
    for (def list : data.value) {
        if (list.list && list.list.template == 'documentLibrary') {
            def libraryName = list.displayName ?: list.name
            if (libraryName.toLowerCase().contains(searchString.toLowerCase())) {
                echo "Found matching library: ${libraryName}"
                return list.id
            }
        }
    }
    
    return null
}

// Function to upload small file
def uploadFile(accessToken, siteUrl, libraryId, filePath) {
    // Check if file exists
    if (!fileExists(filePath)) {
        error("File not found: ${filePath}")
    }
    
    // Get filename from path
    def fileName = filePath.split('/').last()
    def encodedFileName = URLEncoder.encode(fileName, 'UTF-8')
    
    echo "Uploading file: ${fileName}"
    
    // Build upload URL
    def siteUri = new URI(siteUrl)
    def hostname = siteUri.getHost()
    def sitePath = siteUri.getPath()
    def uploadUrl = "https://graph.microsoft.com/v1.0/sites/${hostname}:${sitePath}:/lists/${libraryId}/drive/root:/${encodedFileName}:/content"
    
    // Upload file
    def response = httpRequest(
        httpMode: 'PUT',
        url: uploadUrl,
        customHeaders: [
            [name: 'Authorization', value: "Bearer ${accessToken}"],
            [name: 'Content-Type', value: 'application/octet-stream']
        ],
        uploadFile: filePath,
        validResponseCodes: '200,201'
    )
    
    def jsonSlurper = new JsonSlurper()
    def result = jsonSlurper.parseText(response.content)
    
    return result.id
}
