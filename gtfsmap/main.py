import os
import csv
import sqlite3
import logging
import xml.etree.ElementTree as etree

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO
)

class gtfs(object):
    """Load GTFS data into memory DB"""
    def __init__(self, inputfolder):
        super(gtfs, self).__init__()

        self.name = 'Transport Routes'
        self.description = 'Automatically generated from GTFS data'

        self.inputfolder = os.path.abspath(inputfolder)
        self.db = sqlite3.connect(':memory:')
        self.cursor = self.db.cursor()

        if os.path.isdir(inputfolder):
            logging.info(
                'Loading files from {0}'.format(self.inputfolder)
            )
        else:
            logging.error(
                'Unable to open {0}'.format(self.inputfolder)
            )
            raise IOError

        #: Trigger file load
        self.load_files()

    def load_files(self):
        """Find files to import"""
        for (dirpath, dirnames, filenames) in os.walk(self.inputfolder):
            break
        for fname in filenames:
            self.load_table(
                    os.path.join(dirpath, fname)
            )

    def load_table(self, file_name):
        """Load GTFS CSV into memoryDB"""
        logging.info('Loading file {0}'.format(file_name))
        with open(file_name, 'rb') as f:
            csvfile = csv.reader(f)
            #: Grab first line
            headers = csvfile.next()

            #: Create table and return table name
            table_name = self.build_table(
                headers,
                file_name
            )

            for row in csvfile:
                #: Generate insert SQL with bound params
                insert = "insert into {0} values ({1})".format(
                    table_name,
                    ','.join(['?' for x in range(len(headers))])
                )

                #: Run insert
                self.cursor.execute(insert, row)
                self.db.commit()

    def build_table(self, headers, file_name):
        """Generate table based on CSV header structure"""
        table_name = os.path.basename(os.path.splitext(file_name)[0])
        sql = "create table {0} ({1})".format(
            table_name,
            ', '.join([ "{0} text".format(h) for h in headers])
        )
        self.cursor.execute(sql)
        return(table_name)


class kml(gtfs):
    """Generate KML map"""
    def __init__(self, inputfolder):
        super(kml, self).__init__(inputfolder)
        self.style = etree.fromstring("""
            <Style id="line">
                <LineStyle>
                    <color>7fff7f00</color>
                    <width>4</width>
                </LineStyle>
            </Style>
            """)

    def build_route(self, route_id):
        logging.info('Building route {0}'.format(route_id))

        #: Get data on route
        self.cursor.execute(
    '''
            select * from routes
            inner join trips on routes.route_id = trips.route_id
            where routes.route_id = ?
    '''
            , [route_id, ])
        route_data = self.cursor.fetchone()
        shape_id = route_data[-1]

        #: Generate placemark element
        placemark = etree.Element("Placemark")

        #: Add a name element
        name = etree.Element("name")
        name.text = route_data[2]
        placemark.append(name)

        #: Add a description element
        description = etree.Element("description")
        description.text = route_data[3]
        placemark.append(description)

        #: Add styleUrl
        styleUrl = etree.Element("styleUrl")
        styleUrl.text = "#line"
        placemark.append(styleUrl)

        #: Generate LineString
        LineString = etree.Element("LineString")

        #: Extrude
        extrude = etree.Element("extrude")
        extrude.text = "1"
        LineString.append(extrude)

        #: tessellate
        tessellate = etree.Element("tessellate")
        tessellate.text = "1"
        LineString.append(tessellate)

        #: coordinates
        coordinates = etree.Element("coordinates")
        output = ""
        for row in self.cursor.execute(
                'select shape_pt_lon, shape_pt_lat from shapes where shape_id = ?',
                [shape_id, ]
        ):
            output = output + "{0},{1},0\n".format(row[0], row[1])
        coordinates.text = output
        LineString.append(coordinates)

        #: Add LineString to placemark
        placemark.append(LineString)
        return(placemark)

    def build(self, output_name='Export.kml'):

        kml = etree.Element('kml', xmlns="http://www.opengis.net/kml/2.2")
        document = etree.Element('Document')
        kml.append(document)
        name = etree.Element('name')
        description = etree.Element('description')
        document.append(name)
        document.append(description)
        name.text = self.name
        description.text = self.description
        document.append(self.style)

        routes = []
        for row in self.cursor.execute("select route_id from routes"):
            routes.append(row[0])

        for route in routes:
           document.append(self.build_route(route))

        with open(output_name, 'w') as f:
            f.write(etree.tostring(kml))
