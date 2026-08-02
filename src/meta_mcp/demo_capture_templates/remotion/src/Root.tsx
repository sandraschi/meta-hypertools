import { Composition } from "remotion";
import { DemoComposition, calculateDemoMetadata, type DemoProps } from "./DemoComposition";

export const RemotionRoot: React.FC = () => {
  const defaultProps: DemoProps = {
    title: "Fleet Webapp Demo",
    subtitle: "",
  };

  return (
    <Composition
      id="DemoComposition"
      component={DemoComposition}
      durationInFrames={900}
      fps={30}
      width={1280}
      height={720}
      defaultProps={defaultProps}
      calculateMetadata={calculateDemoMetadata}
    />
  );
};
