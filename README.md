# autoAPI
<kbd><img src="http://adrianmoore.net/autoAPI/images/01TitleBar.png"></kbd>
Create and manipulate a custom API to an XML data set

## How to use

Run the Python application and access it in a web browser, passing the URL of the XML source as the querystring.  For example, with a local installation running on port 5000, we request the XML data shown below by the URL http://localhost:5000/?http://apis.opendata.gov.uk/translink/3042AA.xml.

The application reads the XML file from the source and displays it in a clickable node tree.

<kbd><img src="http://adrianmoore.net/autoAPI/images/02ShowClickableTree.png"></kbd>

Clicking on the "Test API" button generates the JSON equivalent of the XML data.  By default, all fields are selected and the JSON structure matches that of ther original XML. 

<kbd><img src="http://adrianmoore.net/autoAPI/images/03FullJSONResult.png"></kbd>

To filter the data we can select only the station name, the arrival and departure times for each service...

<kbd><img src="http://adrianmoore.net/autoAPI/images/04ChooseFields1.png"></kbd>

... and the origin station and final destination for each service.  We also choose to rename these fields as "ComingFrom" and "GoingTo" to provide more intuitive field names.  Now click on the "Submit" button to store these selections in the database.

<kbd><img src="http://adrianmoore.net/autoAPI/images/05ChooseFields2.png"></kbd>

The details are stored, so we click "Test API" again...

<kbd><img src="http://adrianmoore.net/autoAPI/images/06TestAPI.png"></kbd>

... and only the fields selected are present in the JSON structure.

<kbd><img src="http://adrianmoore.net/autoAPI/images/07SelectedJSONResult.png"></kbd>

We can simplify the JSON returned by choosing the "Collapse JSON" option and re-clicking "Test API".  This removes elements of the structure that do not contain data and collapses the result to its simplest form.

<kbd><img src="http://adrianmoore.net/autoAPI/images/08SelectCollapseOption.png"></kbd>


<kbd><img src="http://adrianmoore.net/autoAPI/images/09CollapsedResult.png"></kbd>

Where the URL contains a variable element that specifies the XML sourcec to be accessed, we can denote this by enclosing the variable part within &lt; and &lt; characters.  Here we specify that "3042AA" is a variable element for which we will supply the actual value to be used.  Click on the "Submit" button to record this in the database.

<kbd><img src="http://adrianmoore.net/autoAPI/images/10Parameterise.png"></kbd>

Now, an extra "Parameter" field is required, in which we provide the value to be substituted into the URL.  We specify "3045CE" as the new station code for which data should be retrieved

<kbd><img src="http://adrianmoore.net/autoAPI/images/11SetParameter.png"></kbd>

Now the data returned is that for a different station as previously.

<kbd><img src="http://adrianmoore.net/autoAPI/images/12DifferentResult.png"></kbd>

The API is used programmatically by submitting a POST request to http://localhost:5000/api/?url, where **url** is the address from where the XML is to be retrieved.  POST variables for **collapseJSONResult**, **eliminateNullValues** and **parameter**  are provided as required.

<kbd><img src="http://adrianmoore.net/autoAPI/images/13Postman.png"></kbd>

auto{API} can also remove null values from the resulting JSON data.  

<kbd><img src="http://adrianmoore.net/autoAPI/images/14Auction1.png"></kbd>


<kbd><img src="http://adrianmoore.net/autoAPI/images/15Auction2.png"></kbd>


<kbd><img src="http://adrianmoore.net/autoAPI/images/16Auction3.png"></kbd>


<kbd><img src="http://adrianmoore.net/autoAPI/images/17Auction4.png"></kbd>


<kbd><img src="http://adrianmoore.net/autoAPI/images/18Auction5.png"></kbd>
