import { useTranslation } from "react-i18next"; 
export default function About() { 
    const { t } = useTranslation(); 
    return <h3>{t("nav.about")}</h3>; 
}