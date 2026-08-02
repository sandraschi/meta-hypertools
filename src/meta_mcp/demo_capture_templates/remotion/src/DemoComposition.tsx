import {
  AbsoluteFill,
  CalculateMetadataFunction,
  Video,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
} from "remotion";
import { getVideoMetadata } from "@remotion/media-utils";

export type DemoProps = {
  title: string;
  subtitle: string;
};

const TitleCard: React.FC<{ title: string; subtitle: string }> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const introFrames = Math.round(fps * 2.5);
  const opacity = interpolate(frame, [0, 12, introFrames - 12, introFrames], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, introFrames], [24, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-start",
        alignItems: "flex-start",
        padding: 48,
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          opacity,
          transform: `translateY(${translateY}px)`,
          background: "rgba(15, 23, 42, 0.82)",
          border: "1px solid rgba(148, 163, 184, 0.35)",
          borderRadius: 16,
          padding: "20px 28px",
          maxWidth: 720,
          boxShadow: "0 20px 60px rgba(0,0,0,0.35)",
        }}
      >
        <div style={{ color: "#f8fafc", fontSize: 34, fontWeight: 700, letterSpacing: -0.5 }}>{title}</div>
        {subtitle ? (
          <div style={{ color: "#cbd5e1", fontSize: 20, marginTop: 8, lineHeight: 1.4 }}>{subtitle}</div>
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

export const DemoComposition: React.FC<DemoProps> = ({ title, subtitle }) => {
  const sourceVideo = staticFile("source.webm");

  return (
    <AbsoluteFill style={{ backgroundColor: "#020617" }}>
      <Video src={sourceVideo} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      <TitleCard title={title} subtitle={subtitle} />
    </AbsoluteFill>
  );
};

export const calculateDemoMetadata: CalculateMetadataFunction<DemoProps> = async () => {
  const sourceVideo = staticFile("source.webm");
  const metadata = await getVideoMetadata(sourceVideo);
  const fps = 30;
  return {
    fps,
    durationInFrames: Math.max(Math.ceil(metadata.durationInSeconds * fps), fps * 3),
    width: metadata.width || 1280,
    height: metadata.height || 720,
  };
};
