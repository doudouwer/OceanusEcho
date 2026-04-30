import { GlobalChrome } from "@/components/layout/GlobalChrome";
import { CareerArcPanel } from "@/components/panels/CareerArcPanel";
import { GenreFlowPanel } from "@/components/panels/GenreFlowPanel";
import { InfluenceGalaxyPanel } from "@/components/panels/InfluenceGalaxyPanel";
import { StarProfilerPanel } from "@/components/panels/StarProfilerPanel";
import styles from "./DashboardLayout.module.css";

export function DashboardLayout() {
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.brandMark} />
          <div>
            <h1 className={styles.title}>OceanusEcho</h1>
            <p className={styles.subtitle}>Linked multiple views / Neo4j / FastAPI / React</p>
          </div>
        </div>
        <GlobalChrome />
      </header>
      <main className={styles.grid}>
        <section className={styles.span2}>
          <InfluenceGalaxyPanel />
        </section>
        <section>
          <CareerArcPanel />
        </section>
        <section>
          <GenreFlowPanel />
        </section>
        <section className={styles.span2}>
          <StarProfilerPanel />
        </section>
      </main>
    </div>
  );
}
