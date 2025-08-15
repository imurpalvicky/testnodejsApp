1node {
    // Set these before usage, or pull via Jenkins credentials plugin
    def clientId = 'YOUR_CLIENT_ID'
    def clientSecret = 'YOUR_CLIENT_SECRET'
    def tenantId = 'YOUR_TENANT_ID'
    def scope = 'https://connect.xyz.com/.default'
    def siteBaseUrl = 'https://share.connect.xyz.com/teams/teststalebranches/DMLRelease'
    def searchTerm = '1769'
    def artifactPath = 'artifact.zip' // Adjust as required

    stage('Get SharePoint Access Token') {
        def tokenResp = httpRequest contentType: 'APPLICATION_FORM',
            httpMode: 'POST',
            requestBody: "client_id=${clientId}&client_secret=${clientSecret}&scope=${scope}&grant_type=client_credentials",
            url: "https://login.microsoftonline.com/${tenantId}/oauth2/v2.0/token"
        def accessToken = new groovy.json.JsonSlurperClassic().parseText(tokenResp.content).access_token
        if (!accessToken) { error "No access token received!" }
        env.ACCESS_TOKEN = accessToken
    }

    stage('Find Document Library') {
        def resp = httpRequest customHeaders: [
                [name: 'Authorization', value: "Bearer ${env.ACCESS_TOKEN}"]
            ],
            url: "${siteBaseUrl}/_api/web/lists"
        def lists = new groovy.json.JsonSlurperClassic().parseText(resp.content)
        def match = lists.value.find { it.Title.toLowerCase().contains(searchTerm.toLowerCase()) }
        if (!match) { error "No document library found containing: ${searchTerm}" }
        env.LIBRARY_TITLE = match.Title
        env.LIBRARY_URL = match.RootFolder.ServerRelativeUrl
        echo "Found: ${env.LIBRARY_TITLE} at ${env.LIBRARY_URL}"
    }

    stage('Upload Artifact') {
        // Read file as binary. For large files, consider chunking.
        def fileData = readFile file: artifactPath, encoding: 'Base64'
        def decoded = fileData.decodeBase64()
        httpRequest httpMode: 'POST',
            customHeaders: [
                [name: 'Authorization', value: "Bearer ${env.ACCESS_TOKEN}"],
                [name: 'Accept', value: 'application/json;odata=verbose']
            ],
            url: "${siteBaseUrl}/_api/web/GetFolderByServerRelativeUrl('${env.LIBRARY_URL}')/Files/add(url='${artifactPath}',overwrite=true)",
            requestBody: decoded,
            contentType: 'APPLICATION_OCTETSTREAM',
            validResponseCodes: '200,201'
        echo "File uploaded"
    }
}
