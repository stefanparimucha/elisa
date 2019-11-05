from elisa import graphics


class Plot(object):
    """
    Universal plot interface for Observer class, more detailed documentation for each value of descriptor is
    available in graphics library.

    Available methods::

        `orbit` - plots orbit in orbital plane

    """

    def __init__(self, instance):
        self._self = instance

    def phase_curve(self, **kwargs):
        """
        Function plots phase curves calculated in Observer class.

        :param kwargs: Dict;
        :**kwargs options**:
            * **phases** * -- numpy.array;
            * **fluxes** * -- Dict;
            * **flux_unit** * -- astropy.units.quantity.Quantity; unit of flux measurements,
            * **legend** * -- bool; on/off,
            * **legend_location** * -- int;
        """
        kwargs['phases'] = kwargs.get('phases', self._self.phases)
        kwargs['fluxes'] = kwargs.get('fluxes', self._self.fluxes)
        kwargs['flux_unit'] = kwargs.get('flux_unit', self._self.fluxes_unit)
        kwargs['legend'] = kwargs.get('legend', True)
        kwargs['legend_location'] = kwargs.get('legend_location', 4)

        graphics.phase_curve(**kwargs)
