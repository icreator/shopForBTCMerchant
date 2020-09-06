# -*- coding: utf-8 -*-

routes_in = (
	(r'/$anything', r'/shop/$anything'),
	)

routes_out = [(x, y) for (y, x) in routes_in]
