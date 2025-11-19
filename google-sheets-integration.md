# Google Sheets Integration

## Setup Steps

### 1. Create the spreadsheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new sheet named "Wedding Confirmations"
3. In the first row, add these headers:
   - `Date` | `Name` | `Attendance` | `With Companions` | `Adults` | `Children` | `Bus` | `Allergies` | `Comments`

### 2. Create the Google Apps Script

1. In your spreadsheet, go to **Extensions** > **Apps Script**
2. Delete the existing code and paste this:

```javascript
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Obtener los parámetros del formulario
    var nombre = e.parameter.nombre || '';
    var asistencia = e.parameter.asistencia || '';
    var acompanado = e.parameter.acompanado || '';
    var adultos = e.parameter.adultos || '0';
    var ninos = e.parameter.ninos || '0';
    var autobus = e.parameter.autobus || 'no';
    var alergias = e.parameter.alergias || '';
    var comentarios = e.parameter.comentarios || '';
    
    // Añadir fila con los datos
    sheet.appendRow([
      new Date(),
      nombre,
      asistencia,
      acompanado,
      adultos,
      ninos,
      autobus,
      alergias,
      comentarios
    ]);
    
    return ContentService
      .createTextOutput(JSON.stringify({success: true}))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch(error) {
    return ContentService
      .createTextOutput(JSON.stringify({success: false, error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

3. Click **Save** (disk icon)
4. Click **Deploy** > **New deployment**
5. Select **Web app**
6. Configure:
   - **Description**: "Wedding Confirmations API"
   - **Execute as**: Your account
   - **Who has access**: Anyone
7. Click **Deploy**
8. **COPY THE URL** it gives you (something like: `https://script.google.com/macros/s/ABC123.../exec`)
9. Click **Authorize access** and accept the permissions

### 3. Update the HTML code

The HTML code is already configured with the script URL. If you need to change it, look for this line in the HTML file:

```javascript
const SCRIPT_URL = 'https://script.google.com/macros/s/YOUR_URL_HERE/exec';
```

### 4. Test

1. Open your website
2. Fill out the form
3. Check that the data appears in your Google Sheet

## Form fields

The current form includes:

- **Full name** (required): Guest name
- **Will you attend the wedding?** (required): Yes / No
- **Will you come with companion(s)?** (required): Yes / No
  - If "Yes" is selected, these appear:
    - **Number of adult companions**: 0-5
    - **Number of child companions**: 0-5
- **Do you need the bus?** (required): One-way / Return / Round trip / No
- **Allergies and intolerances** (optional): Free text
- **Additional comments** (optional): Free text

## Advantages
- ✅ Completely free
- ✅ Data is saved automatically
- ✅ Easy to view and export the data
- ✅ You can share the sheet with your partner or wedding planner
- ✅ No own server required
- ✅ Clear separation between adults and children for planning

## Email notifications (Optional)

If you want to receive an email every time someone confirms, add this to the Google Apps Script:

```javascript
function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // Get form parameters
    var name = e.parameter.name || '';
    var attendance = e.parameter.attendance || '';
    var accompanied = e.parameter.accompanied || '';
    var adults = e.parameter.adults || '0';
    var children = e.parameter.children || '0';
    var bus = e.parameter.bus || 'no';
    var allergies = e.parameter.allergies || '';
    var comments = e.parameter.comments || '';
    
    // Add row with data
    sheet.appendRow([
      new Date(),
      name,
      attendance,
      accompanied,
      adults,
      children,
      bus,
      allergies,
      comments
    ]);
    
    // Build companions information
    var companionsInfo = "No";
    if (accompanied === "yes") {
      companionsInfo = "Yes - Adults: " + adults + ", Children: " + children;
    }
    
    // Send notification email
    var emailBody = 
      "New wedding confirmation:\n\n" +
      "Name: " + name + "\n" +
      "Attendance: " + attendance + "\n" +
      "Accompanied: " + companionsInfo + "\n" +
      "Bus: " + bus + "\n" +
      "Allergies: " + (allergies || "None") + "\n" +
      "Comments: " + (comments || "None");
    
    MailApp.sendEmail({
      to: "your-email@gmail.com", // Change to your email
      subject: "New wedding confirmation - " + name,
      body: emailBody
    });
    
    return ContentService
      .createTextOutput(JSON.stringify({success: true}))
      .setMimeType(ContentService.MimeType.JSON);
      
  } catch(error) {
    return ContentService
      .createTextOutput(JSON.stringify({success: false, error: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}
```

## Useful data analysis

With this structure, you can create formulas in Google Sheets for:

**Total confirmed attendees:**
```
=COUNTIF(C:C,"yes")
```

**Total adults (including main guests who are attending):**
```
=COUNTIF(C:C,"yes") + SUMIF(C:C,"yes",E:E)
```

**Total children:**
```
=SUMIF(C:C,"yes",F:F)
```

**Total number of people:**
```
=COUNTIF(C:C,"yes") + SUMIF(C:C,"yes",E:E) + SUMIF(C:C,"yes",F:F)
```

**People with allergies:**
```
=COUNTIF(G:G,"<>")
```

## Troubleshooting

**Issue**: Data doesn’t reach the sheet
- Check that the script URL is correct
- Make sure you granted permissions to the script
- Confirm the script is deployed with access set to "Anyone"

**Issue**: CORS error
- The code uses `mode: 'no-cors'`, which is correct for Google Apps Script
- You can’t read the response, but the data is still sent

**Issue**: The form doesn’t submit
- Open the browser console (F12) and look for errors
- Check that `SCRIPT_URL` is configured correctly
- Check the console.log output to see what data is being sent

**Issue**: Companions section does not appear
- Check that you selected "Yes" in "Will you come with companion(s)?"
- The section shows/hides automatically based on the selection