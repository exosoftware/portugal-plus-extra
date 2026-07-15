##############################################################################
#
#    Copyright (C) 2026 Exo Software, Lda. (<https://exosoftware.pt>)
#
##############################################################################
from odoo import _, models
from odoo.fields import Command


class PtplusDemoDataWizard(models.TransientModel):
    _inherit = "ptplus.demo.data.wizard"

    def _demo_get_or_create_mailing_list(self, partner):
        name = _("Clientes e Prospects")
        contact_list = self.env["mailing.list"].search([("name", "=", name)], limit=1)
        if contact_list:
            return contact_list
        contact_list = self.env["mailing.list"].create({"name": name})
        self.env["mailing.contact"].create(
            {
                "name": partner.name,
                "email": partner.email or False,
                "list_ids": [Command.set([contact_list.id])],
            }
        )
        return contact_list

    def _demo_generate_email_marketing(self, company, partner):
        log = []
        campaign = self._demo_get_or_create_tag(
            "utm.campaign", _("Campanha de Angariação de Clientes")
        )
        contact_list = self._demo_get_or_create_mailing_list(partner)
        mailing = self.env["mailing.mailing"].create(
            {
                "subject": _("Conheça os nossos serviços de engenharia civil"),
                "body_arch": "<p>%s</p>"
                % _("Descubra os nossos serviços de engenharia civil."),
                # email_from's compute falls back to the acting user's email,
                # which may not be configured in a demo environment; a
                # mailing_type='mail' record requires a non-null value
                # (mailing_mailing_email_from check constraint).
                "email_from": company.email or "%s <demo@example.com>" % company.name,
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([contact_list.id])],
                "campaign_id": campaign.id,
            }
        )
        log.append(_("Campanha de email marketing criada: %s") % mailing.subject)
        return log

    def _demo_generate_sms(self, company, partner):
        log = []
        contact_list = self._demo_get_or_create_mailing_list(partner)
        sms_template = self.env["sms.template"].create(
            {
                "name": _("SMS Confirmação de Visita Técnica"),
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "body": _("Confirmamos a visita técnica agendada. Equipa %s")
                % company.name,
            }
        )
        sms_mailing = self.env["mailing.mailing"].create(
            {
                "subject": _("Confirmação de Visita Técnica"),
                "mailing_type": "sms",
                "sms_template_id": sms_template.id,
                "body_plaintext": sms_template.body,
                "mailing_model_id": self.env["ir.model"]._get("mailing.list").id,
                "contact_list_ids": [Command.set([contact_list.id])],
            }
        )
        log.append(_("Mailing SMS criado: %s") % sms_mailing.subject)
        return log

    def _demo_generate_whatsapp(self, company, partner):
        log = []
        template = self.env["whatsapp.template"].create(
            {
                "name": _("Confirmação de Orçamento"),
                "body": _(
                    "Olá, o seu orçamento foi enviado. Obrigado por escolher a %s."
                )
                % company.name,
                "model_id": self.env["ir.model"]._get("res.partner").id,
                "lang_code": "pt_PT",
                "template_type": "marketing",
                "status": "approved",
            }
        )
        channel = self.env["discuss.channel"].create(
            {
                "name": _("WhatsApp - %s") % partner.name,
                "channel_type": "whatsapp",
                "whatsapp_number": partner.phone or "+351210000000",
                "whatsapp_partner_id": partner.id,
            }
        )
        channel.message_post(
            body=_("Olá! Obrigado pelo contacto, em breve enviaremos o orçamento.")
        )
        log.append(_("Modelo WhatsApp '%s' e conversa demo criados") % template.name)
        return log

    def _demo_generate_marketing_automation(self, company, partner):
        log = []
        campaign = self.env["marketing.campaign"].create(
            {
                "name": _("Fidelização de Clientes"),
                "model_id": self.env["ir.model"]._get("res.partner").id,
            }
        )
        self.env["marketing.activity"].create(
            {
                "name": _("Email de Boas-vindas"),
                "campaign_id": campaign.id,
                "activity_type": "email",
                "trigger_type": "begin",
                "interval_number": 0,
                "interval_type": "hours",
            }
        )
        log.append(_("Campanha de marketing automation criada: %s") % campaign.name)
        return log

    def _demo_generate_helpdesk(self, company, partner):
        log = []
        # The team name must be unique per company: helpdesk.team auto-creates
        # a mail.alias from it, and mail.alias names are unique database-wide,
        # so re-running this for a second company with the same generic name
        # ("Suporte Técnico") collides with the first company's alias.
        team_name = _("Suporte Técnico - %s") % company.name
        team = self.env["helpdesk.team"].search(
            [("name", "=", team_name), ("company_id", "=", company.id)],
            limit=1,
        )
        if not team:
            team = self.env["helpdesk.team"].create(
                {
                    "name": team_name,
                    "company_id": company.id,
                    "member_ids": [Command.link(self.env.uid)],
                }
            )
        tickets = [
            (_("Fissura na parede - necessita vistoria"), "2"),
            (_("Pedido de esclarecimento sobre orçamento"), "0"),
            (_("Atraso na entrega de materiais"), "1"),
        ]
        for name, priority in tickets:
            self.env["helpdesk.ticket"].create(
                {
                    "name": name,
                    "team_id": team.id,
                    "partner_id": partner.id,
                    "priority": priority,
                }
            )
        log.append(_("%s ticket(s) de apoio ao cliente criados") % len(tickets))
        return log
