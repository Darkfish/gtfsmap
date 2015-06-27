from gtfsmap import kml

#: Build map for Wellington with GTFS data stored ../Wellington
wellington = kml('../Wellington')
wellington.name = 'Wellington Public Transport Routes'
wellington.build('Wellington.kml')
