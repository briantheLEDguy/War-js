#pragma once

#include "Dom/JsonObject.h"
#include "HAL/FileManager.h"
#include "Policies/CondensedJsonPrintPolicy.h"
#include "Serialization/JsonSerializer.h"

namespace WarCitadelProofJson
{
    // Stream UTF-8 to the file archive; a complete corridor report must not pass
    // through the 32-bit FString JSON writer's two-gigabyte memory archive.
    inline bool Save(const TSharedRef<FJsonObject>& Object,const FString& Path)
    {
        TUniquePtr<FArchive> Archive(IFileManager::Get().CreateFileWriter(*Path));
        if (!Archive) return false;
        auto Writer=TJsonWriterFactory<UTF8CHAR,TCondensedJsonPrintPolicy<UTF8CHAR>>::Create(Archive.Get());
        const bool Serialized=FJsonSerializer::Serialize(Object,Writer);
        const bool Closed=Archive->Close();
        return Serialized && Closed && !Archive->IsError();
    }

    inline TSharedRef<FJsonObject> RejectedSeedSummary(const TSharedRef<FJsonObject>& Resolution)
    {
        // A rejected lift is never clearance evidence. Preserve every body and
        // typed disposition, but omit its unused triangle certificates. Actual
        // separated query receipts retain all read-locked shape/face evidence.
        auto Summary=MakeShared<FJsonObject>();Summary->Values=Resolution->Values;
        TArray<TSharedPtr<FJsonValue>> Bodies;
        for (const auto& Value:Resolution->GetArrayField(TEXT("perBodyDecisions")))
        {
            auto Body=MakeShared<FJsonObject>();Body->Values=Value->AsObject()->Values;
            Body->RemoveField(TEXT("liveWitness"));Bodies.Add(MakeShared<FJsonValueObject>(Body));
        }
        Summary->SetArrayField(TEXT("perBodyDecisions"),Bodies);
        Summary->SetBoolField(TEXT("rejectedSeedWitnessesOmitted"),true);
        return Summary;
    }
}
