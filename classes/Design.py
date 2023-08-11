import sys
import json
from json import JSONDecodeError
from xml.etree import ElementTree
from xml.dom import minidom
from datetime import datetime
from abc import ABC, abstractmethod
from classes.Config import Config
from classes.Direction import Direction, Rotation
from classes.PathStyle import PathStyle
from classes.Template import Template
from classes.File import File
from classes.ConfigConstants import ConfigConstantsText as Ct
from classes.ConfigConstants import ConfigConstantsTemplate as Cm

""" Order of Configuration is
    Default configuration in insertmaker.config
    Project configuration
    Item configuration
    """


class Design(ABC):
    # number of decimal places for tdpi values
    __PRECISION = 4

    # resolution of the SVG drawing. Standard for the Cricut is 72dpi
    # TODO: Resolution as parameter for the config
    __RESOLUTION = 72

    # Default filename and section for the InsertMaker configuration file
    __DEFAULT_SECTION_NAME = 'STANDARD'
    __DEFAULT_CONFIG_FILE = 'InsertMaker.config'

    # Fallback settings when InsertMaker.config is missing
    __DEFAULT_X_OFFSET = 1.0
    __DEFAULT_Y_OFFSET = 2.0
    __DEFAULT_Y_TEXT_SPACING = 7
    __DEFAULT_THICKNESS = 1.5
    __DEFAULT_STROKE_COLOR = '#aaaaaa'
    __DEFAULT_STROKE_DASHARRAY = '20, 20'
    __DEFAULT_STROKE_WIDTH = 2

    # Default path  and extension definitions
    __TEMPLATE_PATH = 'templates'

    # unit definitions
    __UNIT_MM_TEXT = Ct.unit_mm
    __UNIT_MIL_TEXT = Ct.unit_mil
    __DEFAULT_UNIT = __UNIT_MM_TEXT

    # Default measure keys, text keys
    # x offset       : left offset of the whole SVG drawing
    # y offset       : top offset of the whole SVG drawing
    # y text spacing : vertical spacing of the describing text lines at the bottom of the drawing
    # thickness      : thickness of the uses material
    # stroke width   : stroke width of the lines in the SVG drawing
    __settings_standard_measures = [Ct.x_offset, Ct.y_offset, Ct.y_text_spacing, Ct.thickness, Ct.stroke_width,
                                    Ct.resolution]

    # unit             : used unit in the settings (mm or mil)
    # stroke color     : color of the lines drawn in the SVG image
    # stroke dasharray : pattern of the lines drawn in the SVG image
    # resolution       : resolution of the SVG drawing
    __settings_standard_texts = [Ct.unit, Ct.stroke_color, Ct.stroke_dasharray, Ct.resolution]

    # The nonstandard keys are design dependend and cannot be in the global settings InsertMaker.config
    # title         : title of the drawing
    # filename      : filename of the utput file
    # project name  : project (i.e. boardgame) to which the design belongs
    # template name : SVG template to use for the design
    __settings_nonstandards = [Ct.title, Ct.filename, Ct.project_name, Ct.template_name]

    # all measure keys
    __settings_measures = __settings_standard_measures

    # all text keys. Standard and nonstandard
    __settings_texts = __settings_standard_texts + __settings_nonstandards

    # boolean configuration keys
    __settings_boolean = []

    # enumerations in config
    __settings_enum = {}

    # conversion values for unit<->tdpi
    __conversion_factor = {Ct.unit_mm: (__RESOLUTION * 10000) / 25.4,
                           Ct.unit_mil: (__RESOLUTION * 10000)
                           }

    __default_configuration = {}

    measures = {}

    def __init__(self, args):

        self.config_file_and_section = args.get(Ct.config_file_and_section)

        # default settings
        self.settings = {Ct.x_offset: self.__DEFAULT_X_OFFSET,
                         Ct.y_offset: self.__DEFAULT_Y_OFFSET,
                         Ct.y_text_spacing: self.__DEFAULT_Y_TEXT_SPACING,
                         Ct.thickness: self.__DEFAULT_THICKNESS,
                         Ct.title: f'{__class__.__name__}-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                         Ct.filename: '',
                         Ct.project_name: '',
                         Ct.template_name: '',
                         Ct.unit: self.__DEFAULT_UNIT,
                         Ct.resolution: self.__RESOLUTION,
                         Ct.stroke_color: self.__DEFAULT_STROKE_COLOR,
                         Ct.stroke_width: self.__DEFAULT_STROKE_WIDTH,
                         Ct.stroke_dasharray: self.__DEFAULT_STROKE_DASHARRAY,
                         }

        # Overwrite the internal default config with the settings from the Insertmaker.config
        self.__read_config(f'{self.__DEFAULT_CONFIG_FILE}{Ct.config_separator}{self.__DEFAULT_SECTION_NAME}')

        # Overwrite the combined default/InsertMaker settings with the ones from the command line
        if Ct.options in args:
            options = args.get(Ct.options)
            self.__update_settings_with_options(options)

        self.verbose = args.get(Ct.verbose, False)
        self.noprint = args.get(Ct.noprint, False)

        # corner points for the design
        self.corners: list[float] = []

        # lines for cutting/drawing
        self.cutlines: list[float] = []

        # x and y positions for the boundaries
        self.left_x: float = 0.0
        self.right_x: float = 0.0
        self.top_y: float = 0.0
        self.bottom_y: float = 0.0

        # content for the template
        self.template_variables = {}

        # command line as string
        self.args_string: str = ' '.join(sys.argv[1:])

    @abstractmethod
    def create(self) -> None:
        """ Create the design. Has to be overridden by the Designs
        """
        pass

    def __update_settings_with_options(self, options: dict) -> None:
        """ Updates the settings with the items from the options
        :param options: Options from the command line
        :return:
        """
        self.settings = self.settings | options
        return

    def convert_settings_measures_to_tdpi(self) -> None:
        """
            Convert the measures from their nativ unint (mm/mil) to dpi * 10000 (tdpi)
        :return: nothing
        """

        # remove all keys ending with '_tdpi'.
        # https://stackoverflow.com/questions/11358411/silently-removing-key-from-a-python-dict
        for k in self.__settings_measures:
            # with pop missing keys will not raise an exception
            self.settings.pop(k + Ct.tdpi, None)

        # copy all measure keys to tdpi and add '_tdpi' to the key from the list of measures to be converted
        self.settings.update(
            {k + Ct.tdpi: self.unit_to_tdpi(self.settings[k]) for k in self.__settings_measures})

        return

    def conversion_factor(self) -> float:
        """
        Delivers the factor for a unit to convert to tdpi
        :return: conversion factor
        """
        return Design.__conversion_factor[self.settings[Ct.unit]]

    def unit_to_tdpi(self, value: float) -> int:
        """ Converts a native unit (mm/mil) to tdpi

        :param value: value to be converted
        :return: converted value
        """
        return int(float(value) * self.conversion_factor())

    @classmethod
    def __tdpi_to_dpi(cls, value: str) -> str:
        """
        Converts tdpi to dpi
        :param value: convert to dpi with 4 decimals
        :return: dpi representation of value
        """
        value = str(value)

        # if the length of the string is shorter than the precision then add leading 0 for the division
        if len(value) < Design.__PRECISION + 1:
            value = ('0' * (cls.__PRECISION + 1) + value)[-Design.__PRECISION - 1:]

        # add decimal point
        return value[:-Design.__PRECISION] + '.' + value[-Design.__PRECISION:]

    @staticmethod
    def tdpi_to_dpi(value) -> str:
        """
        Convert tdpi to dpi
        :param value: item or list to convert to dpi
        :return: list of converted values
        """
        if type(value) is list:
            result = [Design.__tdpi_to_dpi(item) for item in value]
        else:
            result = Design.__tdpi_to_dpi(value)
        return result

    @staticmethod
    def draw_line(corners: list, points: list, move_to=True) -> str:
        """
        Draws a line from the start to the end coordinates
        :return: path string with
        """
        path = ""

        start = 1
        if move_to:
            path = f'M {Design.tdpi_to_dpi(corners[points[0]][0])} {Design.tdpi_to_dpi(corners[points[0]][1])} '
        else:
            start = 0

        if start > len(points):
            return ''

        for point in points[start:]:
            x = Design.tdpi_to_dpi(corners[point][0])
            y = Design.tdpi_to_dpi(corners[point][1])
            path += f'L {x} {y} '

        return path

    @staticmethod
    def draw_halfcircle(corners: list, points: list, move_to=True) -> str:
        """
        Draws a half circle SVG path
        :param corners: all points of the drawing
        :param points: start and end points, directon of arc
        :param move_to: Optional. True include an M to move, False not
        :return: string with <path />
        """
        path = ""
        start_x, start_y, end_x, end_y, diameter, rotation = Design.get_coords_for_arc(corners, points)
        radius = int(diameter / 2)

        return Design.draw_arc(start_x, start_y, radius, rotation, end_x, end_y, move_to)


    @staticmethod
    def draw_quartercircle(corners: list, points: list, move_to=True):
        """
        Draws a quarter circle SVG path
        :param corners: all points of the drawing
        :param move_to: Optional. True include an M to move, False not
        :param points: Start and endpoints
        :return: XML string with <path />
        """
        path = ''
        start_x, start_y, end_x, end_y, radius, rotation = Design.get_coords_for_arc(corners, points)

        return Design.draw_arc(start_x, start_y, radius, rotation, end_x, end_y, move_to)

    @staticmethod
    def get_coords_for_arc(corners: list, path: list):
        """
        Extracts start and end coordinates and radius for drawing an arc or arc segment
        :param corners: all corners of drawings
        :param path: start and end points, direction of arc
        :return:
        """
        start_x, start_y = corners[path[0]]
        end_x, end_y = corners[path[1]]

        rotation = path[2]

        radius = abs(end_y - start_y)
        if start_y == end_y:
            radius = abs(end_x - start_x)

        return start_x, start_y, end_x, end_y, radius, rotation.value

    @staticmethod
    def draw_thumbhole_path(corners: list, path: list):
        """
        Creates an --\\----/--- for thumb retrieve
        :param corners: Corners of design
        :param path: path for the thumbhole
        :return:
        """
        start_x, start_y = corners[path[0]]
        smallradius, thumbholeradius, direction, orientation = path[1:]

        delta = {
            Direction.NORTH: [[-smallradius, -smallradius, direction], [0, -2 * thumbholeradius, 1 - direction],
                              [smallradius, -smallradius, direction]],
            Direction.SOUTH: [[smallradius, smallradius, direction], [0, 2 * thumbholeradius, 1 - direction],
                              [-smallradius, smallradius, direction]],
            Direction.WEST: [[-smallradius, -smallradius, 1 - direction], [-2 * thumbholeradius, 0, direction],
                             [-smallradius, +smallradius, 1 - direction]],
            Direction.EAST: [[smallradius, smallradius, 1 - direction], [2 * thumbholeradius, 0, direction],
                             [smallradius, -smallradius, 1 - direction]],
        }

        xmlstring = ''
        for values in delta[orientation]:
            end_x = start_x + values[0]
            end_y = start_y + values[1]
            outstring = Design.draw_arc(start_x, start_y, smallradius, values[2], end_x, end_y)
            xmlstring += outstring
            start_x = end_x
            start_y = end_y

        return xmlstring

    @staticmethod
    def draw_arc(start_x, start_y, radius, direction, end_x, end_y, move_to=True):
        """
        Draws an scg arv
        :param start_x x startcoordinate
        :param start_y y startcoordinate
        :param radius of the arc
        :param end_x x endcoordinate
        :param end_y y endcoordinate
        :param move_to: Optional. True include an M to move, False not
        :return: string with <path />
        """

        output = ''
        if radius == 0:
            return ''

        if move_to:
            output += f'M {Design.tdpi_to_dpi(start_x)} {Design.tdpi_to_dpi(start_y)} '

        output += f'A {Design.tdpi_to_dpi(radius)} {Design.tdpi_to_dpi(radius)} 0 0 {direction} ' \
                  f'{Design.tdpi_to_dpi(end_x)} {Design.tdpi_to_dpi(end_y)}'

        return output

    @staticmethod
    def draw_paths(corners: list, lines: list) -> str:
        """
        Drav path according using the list of lines with the given corners.
        :param corners: corner coordinates
        :param lines: Style and information for drawing lines, arcs, thumbhiles, ...
        :return: XML Path element
        """
        xml_lines = ''
        for command, values in lines:
            if command == PathStyle.LINE:
                xml_lines += Design.draw_line(corners, values)
            elif command == PathStyle.LINE_NOMOVE:
                xml_lines += Design.draw_line(corners, values, move_to=False)
            elif command == PathStyle.QUARTERCIRCLE:
                xml_lines += Design.draw_quartercircle(corners, values)
            elif command == PathStyle.QUARTERCIRCLE_NOMOVE:
                xml_lines += Design.draw_quartercircle(corners, values, move_to=False)
            elif command == PathStyle.HALFCIRCLE:
                xml_lines += Design.draw_halfcircle(corners, values)
            elif command == PathStyle.HALFCIRCLE_NOMOVE:
                xml_lines += Design.draw_halfcircle(corners, values, move_to=False)
            # not yet used
            elif command == PathStyle.THUMBHOLE:
                xml_lines += Design.draw_thumbhole_path(corners, values)
            elif command == PathStyle.PAIR:
                for start, end in zip(values[::2], values[1::2]):
                    xml_lines += Design.draw_line(corners[start], corners[end])

        return f'<path d="{xml_lines.strip()}"/>'

    def set_bounds(self, corners):
        """
        Extracts the top left and bottom right corner of all corner points
        :param corners: all corners of the design
        :return: min x, max x, min y, max y
        """
        self.left_x = min(x for (x, y) in corners)
        self.top_y = min(y for (x, y) in corners)
        self.right_x = max(x for (x, y) in corners)
        self.bottom_y = max(y for (x, y) in corners)

        return self.left_x, self.right_x, self.top_y, self.bottom_y

    def write_to_file(self, template_values: dict):
        """
        Fills the template with the values from the dict and writes it to a file
        :param template_values:
        :return:
        """

        if self.settings.get(Ct.filename).strip() == '':
            raise 'No filename given'

        template_values[Cm.template_name] = self.settings.get(Ct.template_name, '')

        if Ct.template.strip() == '':
            raise 'No template given'

        if Cm.viewbox_x not in template_values:
            raise 'VIEWBOX X is missing'

        if Cm.viewbox_y not in template_values:
            raise 'VIEWBOX Y is missing'

        template_string = Template.load_template(template_values[Ct.template])

        self.template_variables[Cm.unit] = self.settings.get(Ct.unit, self.__DEFAULT_UNIT)

        # modify FILENAME with leading and trailing $
        self.template_variables[Cm.footer_project_name] = self.settings.get(Ct.project_name, '')
        self.template_variables[Cm.footer_title] = self.settings.get(Ct.title, '')
        self.template_variables[Cm.header_title] = self.settings.get(Ct.title, '')

        self.template_variables[Cm.footer_filename] = self.settings.get(Ct.filename, '')
        self.template_variables[Cm.footer_args_string] = self.args_string
        self.template_variables[Cm.footer_overall_width] = round(
            self.template_variables[Cm.viewbox_x] / self.conversion_factor(), 2)
        self.template_variables[Cm.footer_overall_height] = round(
            self.template_variables[Cm.viewbox_y] / self.conversion_factor(), 2)

        self.template_variables[Cm.label] = self.tdpi_to_dpi(self.left_x)

        ycoord = self.template_variables[Cm.viewbox_y]
        self.template_variables[Cm.label_project_y] = self.tdpi_to_dpi(
            ycoord + self.settings[Ct.y_text_spacing_tdpi])
        self.template_variables[Cm.label_y_spacing] = self.tdpi_to_dpi(self.settings[Ct.y_text_spacing_tdpi])

        all_footers = [i for i in self.template_variables if i.startswith(Cm.footer_dash)]
        self.template_variables[Cm.viewbox] = f'{self.tdpi_to_dpi(self.template_variables[Cm.viewbox_x])} ' \
                                              f' {self.tdpi_to_dpi(self.template_variables[Cm.viewbox_y] + (len(all_footers) + 2) * self.settings[Ct.y_text_spacing_tdpi])} '

        for key in template_values:
            template_string = template_string.replace(key, str(template_values[key]))

        template_string = self.remove_xml_labels(template_string)

        with open(f'{self.settings.get(Ct.filename)}', 'w') as f:
            f.write(template_string)

    def remove_xml_labels(self, template_string):
        if self.noprint is False:
            return template_string

        root = ElementTree.fromstring(template_string)
        for elem in root.iter():
            if 'id' in elem.attrib and elem.attrib['id'] == 'document-labels':
                root.remove(elem)

        ElementTree.register_namespace('', 'http://www.w3.org/2000/svg')
        newdom = minidom.parseString(ElementTree.tostring(root))
        xmlstr = '\n'.join([line for line in newdom.toprettyxml(indent=' ' * 2).split('\n') if line.strip()])

        return xmlstr

    def tdpi_to_unit(self, value: int) -> float:
        """
        Convert values from tdpi to the unit from the settings

        :param value: tdpi to convert
        :return: unit
        """

        return round(value / self.conversion_factor(), 2)

    def unit_to_dpi(self, value: float) -> float:
        """
        convert measure from mil/mm to DPI
        :param value: value to convert
        :return: DPI value
        """
        return int(value * self.conversion_factor()) / (10 ** self.__PRECISION)

    def add_settings_boolean(self, keys: list) -> None:
        """
        Add list of config keys that represent a boolean value

        :param keys: keys to add to boolean config list
        :return:
        """
        self.__settings_boolean = self.__settings_boolean + keys

    def add_settings_enum(self, keys: dict) -> None:
        """
        Add list of config keys that represent an enum value

        :param keys: keys to add to enum config list
        :return:
        """
        self.__settings_enum.update(keys)

    def add_settings_measures(self, keys: list) -> None:
        """
        Add list of config measure keys to standard measure keys for converting unit -> tdpi
        :param keys: list of keys
        :return:
        """
        self.__settings_measures = self.__settings_measures + keys

    def add_config_texts(self, texts: list) -> None:
        """
        Add list of text config text keys. These are nonstandard keys
        :param texts:
        :return:
        """
        self.__settings_texts += texts

    def set_title_and_outfile(self, default_title: str) -> None:
        """
        Set the title of the sheet and the filename for the output
        :param default_title: title used when no title in the settings
        :return:
        """
        if default_title is None or default_title.strip() == '':
            return

        if Ct.title not in self.settings:
            # set default title
            self.settings[Ct.title] = default_title

        # set default filename for output
        self.settings[Ct.filename] = File.set_svg_extension(self.settings.get(Ct.filename, default_title))

    def load_settings(self, config_file_and_section: str) -> None:
        """
        Reads in a section from a configuration file.
        :param config_file_and_section: filename with path of the config file
        :param verbose: be verbose of the import
        :param payload: default and optional values
        :return: config object
        """
        self.__read_config(config_file_and_section)

        self.set_title_and_outfile(f'{self.__class__.__name__}-{datetime.now().strftime("%Y%m%d-%H%M%S")}')

    def __read_config(self, filename_and_section: str):
        """ Read configuration from file and convert numbers from string to int/float

        :param filename_and_section Filename and section of configuration to load
        """

        error = ""
        config = Config.read_config(filename_and_section)
        filename, section = Config.get_config_file_and_section(filename_and_section)

        # copy values of all key in the config to the settings. Convert numbers from string to int/float
        self.settings.update({k: self.try_float(config.get(section, k)) for k in config.options(section) if
                              config.has_option(section, k) and section not in self.__settings_enum})

        # iterate through all enums of the settings
        for key in self.__settings_enum:
            # enum_item is a dict with settings name as the key and the enm as value
            # test if the config file has the key
            if config.has_option(section, key):
                # retrieve the data from the config
                value = config.get(section, key)
                try:
                    # convert the config data into an enum by string
                    self.settings[key] = self.__settings_enum[key](value)
                except ValueError as e:
                    error += f'Unknown value for {key} in {filename} section {section}. Current value \'{value}\'. ' \
                             f'Allowed values are {[e.value for e in self.__settings_enum[key]]}'

        # iterate through all boolean settings
        for key in self.__settings_boolean:
            if config.has_option(section, key):
                self.settings[key] = False
                value = config.get(section, key)
                if value.lower() in ['y', 'yes', '1', 't', 'true']:
                    self.settings[key] = True

        if len(error) != 0:
            print(error)
            sys.exit(1)

        return config

    @staticmethod
    def is_float(value):
        try:
            float(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def try_float(value: str):

        try:
            if value.__contains__('.'):
                float(value)
                return float(value)
            else:
                int(value)
                return int(value)
        except ValueError:
            return value

    def get_project_name_for_title(self, prefix='', postfix='-'):
        return f'{"" if len(self.settings.get(Ct.project_name)) == 0 else prefix + self.settings.get(Ct.project_name) + postfix}'

    def get_viewbox(self, x: int, y: int) -> (int, int):
        return round(self.settings.get(Ct.x_offset_tdpi) + x), round(self.settings.get(Ct.y_offset_tdpi) + y)

# found things to consider in later designs
#     self.measures.update({k: args['options'][k] for k in keys if k in args['options']})

# https://stackoverflow.com/questions/23662280/how-to-log-the-contents-of-a-configparser
# print({section: dict(config[section]) for section in config.sections()})

# How to pretty print nested dictionaries?
# https://stackoverflow.com/questions/3229419/how-to-pretty-print-nested-dictionaries
