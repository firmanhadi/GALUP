import sys
import os
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing, QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterVectorDestination,
                       QgsProcessingParameterField,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterDistance,
                       QgsProcessingParameterEnum,
                       QgsProcessingParameterString)
from pylusat import interpolate


class InverseDistanceWeighting(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    INTERPOLATE = "INTERPOLATE"
    INTERPOLATE_FIELD = "INTERPOLATE_FIELD"
    POWER = "POWER"
    NUMBER_NEIGHBOR = "NUMBER_NEIGHBOR"
    SEARCH_RADIUS = "SEARCH_RADIUS"
    DATA_TYPE = "DATA_TYPE"
    OUTPUT_FIELD = "OUTPUT_FIELD"
    OUTPUT = "IDW_output"

    def tr(self, string, context=''):
        if context == '':
            context = self.__class__.__name__
        return QCoreApplication.translate(context, string)

    def group(self):
        return self.tr("LUCIS-OPEN for QGIS")

    def groupId(self):
        return "lucisopen"

    def name(self):
        return "idw"

    def displayName(self):
        return self.tr("Inverse Distance Weighting")

    def shortHelpString(self):
        return self.tr("Inverse distance weighting (IDW)\n"
                       "This function implements an `IDW interpolation"
                       "<https://en.wikipedia.org/wiki/Inverse_distance_weighting>`. "
                       "The power parameter dictates how fast the influence "
                       "to a given location by its nearby objects decays. "
                       "`idw_cv`, a k-fold cross validation method is offered "
                       "to determine the most appropriate value of the "
                       "`power` parameter.")

    def createInstance(self):
        return InverseDistanceWeighting()

    def __init__(self):
        super().__init__()
        self.data_type = (
            ('Integer', self.tr('Integer')),
            ('Float', self.tr('Float'))
        )

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                types=[QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INTERPOLATE,
                self.tr('Interpolation layer'),
                types=[QgsProcessing.TypeVectorAnyGeometry]
            )
        )
        self.addParameter(
            QgsProcessingParameterField(
                self.INTERPOLATE_FIELD,
                self.tr('Interpolating field'),
                parentLayerParameterName=self.INTERPOLATE,
                type=QgsProcessingParameterField.Numeric
            )
        )
        power = QgsProcessingParameterNumber(
            self.POWER,
            self.tr('Power parameter for interpolation'),
            type=QgsProcessingParameterNumber.Double,
            defaultValue=2,
            optional=True
        )
        power.setMetadata({
            'widget_wrapper': {
                'decimals': 2
            }
        })
        self.addParameter(power)
        self.addParameter(
            QgsProcessingParameterNumber(
                self.NUMBER_NEIGHBOR,
                self.tr('Number of neighbors'),
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=12,
                optional=True
            )
        )
        search_radius = QgsProcessingParameterDistance(
            self.SEARCH_RADIUS,
            self.tr('Search radius'),
            defaultValue=None,
            parentParameterName=self.INTERPOLATE,
            optional=True
        )
        search_radius.setMetadata({
            'widget_wrapper': {
                'decimals': 2
            }
        })
        self.addParameter(search_radius)
        self.addParameter(
            QgsProcessingParameterEnum(
                self.DATA_TYPE,
                self.tr('Output data type'),
                options=[dtype[1] for dtype in self.data_type],
                defaultValue=1,
                optional=True
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                name=self.OUTPUT_FIELD,
                description=self.tr('Output field name'),
            )
        )
        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_lyr = self.parameterAsVectorLayer(parameters, self.INPUT, context)
        interpolate_lyr = self.parameterAsVectorLayer(parameters,
                                                      self.INTERPOLATE,
                                                      context)
        interpolate_clm = self.parameterAsString(parameters,
                                                 self.INTERPOLATE_FIELD,
                                                 context)
        power = self.parameterAsDouble(parameters, self.POWER, context)
        n_neighbor = self.parameterAsInt(parameters, self.NUMBER_NEIGHBOR,
                                         context)
        search_radius = self.parameterAsDouble(parameters, self.SEARCH_RADIUS,
                                               context)
        data_type = self.parameterAsEnum(parameters, self.DATA_TYPE, context)
        output_clm = self.parameterAsString(parameters, self.OUTPUT_FIELD, context)
        output_file = self.parameterAsOutputLayer(parameters, self.OUTPUT,
                                                  context)

        sys.path.insert(1, os.path.dirname(os.path.realpath(__file__)))
        from .loqlib import LUCISOpenQGISUtils

        feedback.pushInfo(str(search_radius))

        input_gdf = LUCISOpenQGISUtils.vector_to_gdf(input_lyr)
        interpolate_gdf = LUCISOpenQGISUtils.vector_to_gdf(interpolate_lyr)
        data_type = int if data_type == 0 else float
        input_gdf[output_clm] = interpolate.idw(input_gdf, interpolate_gdf,
                                                interpolate_clm, power,
                                                n_neighbor, search_radius,
                                                dtype=data_type)
        input_gdf.to_file(output_file)
        return {self.OUTPUT: output_file}
