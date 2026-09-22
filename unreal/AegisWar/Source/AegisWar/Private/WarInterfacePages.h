#pragma once
#include "CoreMinimal.h"
class SWidget;
class AWarPlayerController;
TSharedRef<SWidget> WarBuildAtlas(AWarPlayerController* Controller, bool bCampaign, bool bClean = false);
TSharedRef<SWidget> WarBuildGuide(AWarPlayerController* Controller);
TSharedRef<SWidget> WarBuildGmTools(AWarPlayerController* Controller);
