import type { ReactNode } from "react";
import styles from "./PanelCard.module.css";

export function PanelCard({
  title,
  tag,
  description,
  children,
}: {
  title: string;
  tag: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <article className={styles.card}>
      <header className={styles.head}>
        <h2>{title}</h2>
        <span className={styles.tag}>{tag}</span>
      </header>
      <p className={styles.desc}>{description}</p>
      <div className={styles.body}>{children}</div>
    </article>
  );
}
