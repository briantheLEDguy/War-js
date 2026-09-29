#pragma once
#include "CoreMinimal.h"
#include "Dom/JsonObject.h"
class AWarPlayerController;
namespace WarScenarioTransport
{
    using FReply=TFunction<void(bool,TSharedPtr<FJsonObject>,FString)>;
    AEGISWAR_API TSharedPtr<FJsonObject> ReadConfig(const FString& Path);
    AEGISWAR_API void Request(const FString& Url,const FString& Key,const FString& Verb,const FString& Path,
        TSharedPtr<FJsonObject> Body,FReply Reply);
    AEGISWAR_API TSharedPtr<FJsonObject> Capture(AWarPlayerController* PC,const FString& Id);
    AEGISWAR_API bool Restore(AWarPlayerController* PC,const TSharedPtr<FJsonObject>& Character,bool Siege,FString& Error);
}
