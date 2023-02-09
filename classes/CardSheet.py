from datetime import datetime
from classes.Design import Design
from classes.PathStyle import PathStyle
from classes.Template import Template
from classes.Direction import Rotation


class CardSheet(Design):
    # Default values
    __DEFAULT_FILENAME: str = "CardSheet"
    __DEFAULT_TEMPLATE: str = "CardSheet.svg"
    __DEFAULT_TEMPLATE_CARD: str = "Card.svg"

    # number of rows and columns of cards per sheet
    __DEFAULT_COLUMNS: int = 2
    __DEFAULT_ROWS: int = 4

    # distance between single rows and columns
    __DEFAULT_X_SEPARATION: float = 0.0
    __DEFAULT_Y_SEPARATION: float = 0.0

    # corner radius of the cards. 0.0 produces rectangular cards
    __DEFAULT_CORNER_RADIUS: float = 3.0

    # standard size of cards is European
    __DEFAULT_UNIT = "mm"
    __DEFAULT_X_MEASURE: float = 89.0
    __DEFAULT_Y_MEASURE: float = 55.0

    # Enums
    # TODO: Inner class enums?
    __CUTLINES_CARD_FULL: int = 0
    __CUTLINES_CARD_LEFT_OPEN: int = 1
    __CUTLINES_CARD_TOP_OPEN: int = 2
    __CUTLINES_CARD_TOPLEFT_OPEN: int = 3

    def __init__(self, config_file: str, section: str, verbose=False, **kwargs):
        super().__init__(kwargs)

        self.settings.update({'x measure': self.__DEFAULT_X_MEASURE,
                              'y measure': self.__DEFAULT_Y_MEASURE,
                              'corner radius': self.__DEFAULT_CORNER_RADIUS,
                              'x separation': self.__DEFAULT_X_SEPARATION,
                              'y separation': self.__DEFAULT_Y_SEPARATION,
                              'rows': self.__DEFAULT_ROWS,
                              'columns': self.__DEFAULT_COLUMNS,
                              'template name': self.__DEFAULT_TEMPLATE,
                              'template card name': self.__DEFAULT_TEMPLATE,

                              })
        self.add_settings_measures(["x measure", "y measure", "corner radius", "x separation", "y separation"])

        # : encloses config values to replace
        self.settings[
            "title"] = f"{'' if len(self.settings['project name']) == 0 else self.settings['project name'] + '-'}" \
                       f"{self.__DEFAULT_FILENAME}-{self.settings['x measure']}-{self.settings['y measure']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        self.load_settings(config_file, section, verbose)

        self.convert_measures_to_tdpi()

    def create(self):
        # noinspection DuplicatedCode
        self.__init_design()

        card_template = Template.load_template(self.__DEFAULT_TEMPLATE_CARD)

        if self.settings["corner radius"] == 0:
            base_cut = [self.draw_lines(self.corners, self.cutlines_nocorners[self.__CUTLINES_CARD_FULL]),
                        self.draw_lines(self.corners, self.cutlines_nocorners[self.__CUTLINES_CARD_TOP_OPEN]),
                        self.draw_lines(self.corners, self.cutlines_nocorners[self.__CUTLINES_CARD_LEFT_OPEN]),
                        self.draw_lines(self.corners, self.cutlines_nocorners[self.__CUTLINES_CARD_TOPLEFT_OPEN])
                        ]
        else:
            base_cut = [self.draw_lines(self.corners, self.cutlines[self.__CUTLINES_CARD_FULL]),
                        self.draw_lines(self.corners, self.cutlines[self.__CUTLINES_CARD_TOP_OPEN]),
                        self.draw_lines(self.corners, self.cutlines[self.__CUTLINES_CARD_LEFT_OPEN]),
                        self.draw_lines(self.corners, self.cutlines[self.__CUTLINES_CARD_TOPLEFT_OPEN])
                        ]

        rows = self.settings["rows"]
        columns = self.settings["columns"]
        x_separation = self.settings["x separation"]
        y_separation = self.settings["y separation"]
        x_measure = self.settings["x measure"]
        y_measure = self.settings["y measure"]

        output = ""
        for row in range(rows):
            for col in range(columns):
                svgpath = base_cut[self.__CUTLINES_CARD_FULL]

                if x_separation == 0.0 and y_separation != 0.0 and col != 0:
                    # Cards are ordered in rows. Left is full others left open
                    svgpath = base_cut[self.__CUTLINES_CARD_LEFT_OPEN]

                if x_separation != 0.0 and y_separation == 0.0 and row != 0:
                    # Cards are ordered in columns. Top is full others left open
                    svgpath = base_cut[self.__CUTLINES_CARD_TOP_OPEN]

                if x_separation == 0.0 and y_separation == 0.0:
                    # No Separation
                    if row == 0 and col != 0:
                        svgpath = base_cut[self.__CUTLINES_CARD_LEFT_OPEN]
                    elif row != 0 and col == 0:
                        svgpath = base_cut[self.__CUTLINES_CARD_TOP_OPEN]
                    elif row != 0 and col != 0:
                        svgpath = base_cut[self.__CUTLINES_CARD_TOPLEFT_OPEN]

                template = {'$ID$': f"{row} - {col}",
                            '$SVGPATH$': svgpath,
                            '$TRANSLATE$': str(
                                self.to_dpi(
                                    self.settings["x offset"] + (x_measure + x_separation) * col)) + ", " + str(
                                self.to_dpi(self.settings["y offset"] + (y_measure + y_separation) * row))
                            }

                temp = card_template
                for key in template:
                    temp = temp.replace(key, str(template[key]))

                output += temp

        self.template["TEMPLATE"] = self.__DEFAULT_TEMPLATE
        self.template["$SVGPATH$"] = output

        self.template["$FOOTER_CARD_WIDTH$"] = str(self.settings["x measure"]) + " " + self.settings["unit"]
        self.template["$FOOTER_CARD_HEIGHT$"] = str(self.settings["y measure"]) + " " + self.settings["unit"]

        viewbox_x = round(self.settings["x offset_tdpi"] + (self.right_x - self.left_x) * columns
                          + x_separation * self.conversion_factor() * (columns - 1))
        viewbox_y = round(self.settings["y offset_tdpi"] + (self.bottom_y - self.top_y) * rows
                          + y_separation * self.conversion_factor() * (rows - 1))

        self.template["VIEWBOX_X"] = viewbox_x
        self.template["VIEWBOX_Y"] = viewbox_y

        self.write_to_file(self.template)
        print(f"CardSheet \"{self.settings['filename']}\" created")

    def __init_design(self):

        # -----------------------------------------------------------------------------
        #       a  b                        c  d
        #
        #  m    0--4------------------------8-12
        #       |                              |
        #       |                              |
        #  n    1  5                        9 13
        #       |                              |
        #       |                              |
        #       |                              |
        #       |                              |
        #  o    2  6                       10 14
        #       |                              |
        #       |                              |
        #  p    3--7-----------------------11-15

        # Separation x = 0
        # |--------|--------|
        # |  F     |  LO    |
        # |--------|--------|
        #
        # |--------|--------|
        # |  F     |  LO    |
        # |--------|--------|

        # Separation y = 0
        # |--------| |--------|
        # |   F    | |   F    |
        # |--------| |--------|
        # |   TO   | |   TO   |
        # |--------| |--------|

        # Separation x = 0, y = 0
        # |--------|--------|
        # |   F    |  LO    |
        # |--------|--------|
        # |   TO   |  TLO   |
        # |--------|--------|

        x_measure = self.settings["x measure_tdpi"]
        y_meaure = self.settings["y measure_tdpi"]
        corner_radius = self.settings["corner radius_tdpi"]
        x_offset = self.settings["x offset_tdpi"]
        y_offset = self.settings["y offset_tdpi"]

        # X - Points
        a = 0
        b = a + corner_radius
        d = a + x_measure
        c = d - corner_radius

        # Y - Points
        m = 0
        n = m + corner_radius
        p = m + y_meaure
        o = p - corner_radius

        self.corners = [[a, m], [a, n], [a, o], [a, p],
                        [b, m], [b, n], [d, o], [b, p],
                        [c, m], [c, n], [c, o], [c, p],
                        [d, m], [d, n], [d, o], [d, p]
                        ]

        self.cutlines = [
            [
                # Full Card
                [PathStyle.LINE, [4, 8]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [8, 13, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [14]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [14, 11, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [11, 7]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [7, 2, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [2, 1]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [1, 4, Rotation.CW]],
            ],
            [
                # Top open
                [PathStyle.QUARTERCIRCLE, [8, 13, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [14]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [14, 11, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [11, 7]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [7, 2, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [2, 1]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [1, 4, Rotation.CW]],
            ],
            [
                # Left open
                [PathStyle.QUARTERCIRCLE, [1, 4, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [8]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [8, 13, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [14]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [14, 11, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [11, 7]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [7, 2, Rotation.CW]],
            ],
            [
                # Top and left open
                [PathStyle.QUARTERCIRCLE, [8, 13, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [14]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [14, 11, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [11, 7]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [7, 2, Rotation.CW]],
                [PathStyle.LINE_NOMOVE, [2, 1]],
                [PathStyle.QUARTERCIRCLE_NOMOVE, [1, 4, Rotation.CW]],
            ],
        ]

        self.cutlines_nocorners = [
            [
                # Full Card
                [PathStyle.LINE, [0, 12, 15, 3, 0]],
            ],
            [
                # Top open
                [PathStyle.LINE, [12, 15, 3, 0]],
            ],
            [
                # Left open
                [PathStyle.LINE, [0, 12, 15, 3]],
            ],
            [
                # Top and left open
                [PathStyle.LINE, [12, 15, 3]],
            ],

        ]

        # detect boundaries of drawing
        self.set_bounds(self.corners)


def __print_variables(self):
    print(self.__dict__)
