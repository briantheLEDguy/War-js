#include "WarScenarioTransport.h"
#include "WarPlayerController.h"
#include "WarPlayerState.h"
#include "WarCharacter.h"
#include "WarCharacterVisualDefinition.h"
#include "WarContentSubsystem.h"
#include "Engine/GameInstance.h"
#include "HttpModule.h"
#include "Interfaces/IHttpResponse.h"
#include "Interfaces/IHttpRequest.h"
#include "Serialization/JsonSerializer.h"
#include "JsonObjectConverter.h"
#include "Misc/FileHelper.h"

TSharedPtr<FJsonObject> WarScenarioTransport::ReadConfig(const FString& Path)
{
    FString Text; TSharedPtr<FJsonObject> Value;
    if (FFileHelper::LoadFileToString(Text,*Path)) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text),Value);
    return Value;
}
void WarScenarioTransport::Request(const FString& Url,const FString& Key,const FString& Verb,const FString& Path,
    TSharedPtr<FJsonObject> Body,FReply Reply)
{
    if (UE_BUILD_SHIPPING || Key.Len()<32 || !(Url.StartsWith(TEXT("http://")) || Url.StartsWith(TEXT("https://"))))
    { Reply(false,nullptr,TEXT("Scenario development host is not configured."));return; }
    auto Request=FHttpModule::Get().CreateRequest();
    Request->SetURL(Url+Path);Request->SetVerb(Verb);Request->SetTimeout(15);
    Request->SetHeader(TEXT("Authorization"),TEXT("Bearer ")+Key);Request->SetHeader(TEXT("Content-Type"),TEXT("application/json"));
    if (Body) { FString Text;FJsonSerializer::Serialize(Body.ToSharedRef(),TJsonWriterFactory<>::Create(&Text));Request->SetContentAsString(Text); }
    const auto Completed=MakeShared<bool>(false);
    Request->OnProcessRequestComplete().BindLambda([Reply=MoveTemp(Reply),Completed](FHttpRequestPtr,FHttpResponsePtr Response,bool Connected) mutable {
        if (*Completed) return;*Completed=true;
        TSharedPtr<FJsonObject> Json;const TSharedPtr<FJsonObject>* Data=nullptr;FString Error;
        if (Response) FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Response->GetContentAsString()),Json);
        if (Connected && Response && EHttpResponseCodes::IsOk(Response->GetResponseCode()) && Json && Json->TryGetObjectField(TEXT("data"),Data))
        { Reply(true,*Data,FString());return; }
        if (!Json || !Json->TryGetStringField(TEXT("error"),Error)) Error=TEXT("Scenario host unavailable. Start npm run scenario:host on the host computer, then select Connect / retry. Your campaign character is retained.");
        Reply(false,nullptr,Error);
    });
    if (!Request->ProcessRequest()) Request->OnProcessRequestComplete().ExecuteIfBound(Request,nullptr,false);
}
TSharedPtr<FJsonObject> WarScenarioTransport::Capture(AWarPlayerController* PC,const FString& Id)
{
    auto* PS=PC ? PC->GetPlayerState<AWarPlayerState>() : nullptr;
    auto* Pawn=PC ? Cast<AWarCharacter>(PC->GetPawn()) : nullptr;
    if (!PS || !Pawn || !PC->HasAuthority() || !Pawn->IsVisualReady() || Pawn->IsDead() || !Pawn->GetVisualDefinition()) return nullptr;
    auto Result=MakeShared<FJsonObject>();
    Result->SetStringField(TEXT("id"),Id);Result->SetStringField(TEXT("name"),PS->GetPlayerName());
    Result->SetStringField(TEXT("realm"),PS->GetRealm()==EWarRealm::Riftbound ? TEXT("riftbound") : TEXT("aegis"));
    Result->SetStringField(TEXT("visual"),Pawn->GetVisualDefinition()->GetPathName());
    Result->SetStringField(TEXT("returnMap"),UWorld::RemovePIEPrefix(PC->GetWorld()->GetOutermost()->GetName()));
    const FVector Position=Pawn->GetActorLocation();
    Result->SetArrayField(TEXT("returnPosition"),{MakeShared<FJsonValueNumber>(Position.X),MakeShared<FJsonValueNumber>(Position.Y),MakeShared<FJsonValueNumber>(Position.Z)});
    auto Document=MakeShared<FJsonObject>();auto Inventory=MakeShared<FJsonObject>();
    FJsonObjectConverter::UStructToJsonObject(FWarInventorySnapshot::StaticStruct(),&PS->GetInventory(),Inventory,0,0);
    Document->SetObjectField(TEXT("inventory"),Inventory);Document->SetStringField(TEXT("zone"),PS->GetCurrentZone().ToString());
    Document->SetObjectField(TEXT("runtime"),PS->CaptureScenarioState());
    Result->SetObjectField(TEXT("document"),Document);return Result;
}
bool WarScenarioTransport::Restore(AWarPlayerController* PC,const TSharedPtr<FJsonObject>& Character,bool Siege,FString& Error)
{
    if (!PC || !PC->HasAuthority() || !Character) return false;
    auto* PS=PC->GetPlayerState<AWarPlayerState>();
    FString VisualPath,Realm,Name,Id;const TSharedPtr<FJsonObject>* Document=nullptr;const TSharedPtr<FJsonObject>* Inventory=nullptr;
    if (!PS || !Character->TryGetStringField(TEXT("visual"),VisualPath) || !VisualPath.StartsWith(TEXT("/Game/"))
        || !Character->TryGetStringField(TEXT("realm"),Realm) || (Realm!=TEXT("aegis") && Realm!=TEXT("riftbound"))
        || !Character->TryGetStringField(TEXT("name"),Name) || !Character->TryGetStringField(TEXT("id"),Id)
        || !Character->TryGetObjectField(TEXT("document"),Document) || !(*Document)->TryGetObjectField(TEXT("inventory"),Inventory))
    { Error=TEXT("Invalid trusted scenario character document.");return false; }
    const EWarRealm Side=Realm==TEXT("aegis") ? EWarRealm::Aegis : EWarRealm::Riftbound;
    auto* Visual=LoadObject<UWarCharacterVisualDefinition>(nullptr,*VisualPath);
    auto* Content=PC->GetGameInstance()->GetSubsystem<UWarContentSubsystem>();
    FWarInventorySnapshot Snapshot;
    if (!Visual || !Visual->ValidateForSpawn(Side,Error) || !Content || !Content->ValidatePlayableVisual(Visual,Error)
        || !FJsonObjectConverter::JsonObjectToUStruct((*Inventory).ToSharedRef(),&Snapshot,0,0)) return false;
    if (PS->GetRealm()!=EWarRealm::None && PS->GetRealm()!=Side) { Error=TEXT("Scenario character realm mismatch.");return false; }
    PS->SetDevelopmentRealm(Side);PS->SetPlayerName(Name);PS->RestoreScenarioInventory(Snapshot);
    PC->ScenarioCharacterId=Id;
    if (Siege) PS->UseScenarioEarnedAbilities();
    FString Zone;(*Document)->TryGetStringField(TEXT("zone"),Zone);
    PS->SetCurrentZoneTrusted(Siege ? FName(TEXT("aegis_capital")) : FName(*Zone));
    PC->BeginCharacterEntry(Visual);return true;
}
