# -*- coding: utf-8 -*-
#
# Copyright (C) 2025 Cottage Labs.
#
# invenio-aisearch is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Adds an AI-powered search interface to InvenioRDM."""

from flask import Blueprint, render_template
from invenio_i18n import gettext as _

blueprint = Blueprint(
    "invenio_aisearch",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@blueprint.route("/aisearch")
def search():
    """Render the AI search interface."""
    return render_template(
        "invenio_aisearch/search.html",
        page_title=_("AI Search"),
    )


@blueprint.route("/aisearch/similar/<record_id>")
def similar(record_id):
    """Render the similar records interface."""
    return render_template(
        "invenio_aisearch/similar.html",
        page_title=_("Similar Records"),
        record_id=record_id,
    )


@blueprint.route("/aisearch/passages")
def passages():
    """Render the passage search interface."""
    return render_template(
        "invenio_aisearch/passages.html",
        page_title=_("Passage Search"),
    )
